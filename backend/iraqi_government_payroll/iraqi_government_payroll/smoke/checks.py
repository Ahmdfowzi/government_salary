# Copyright (c) 2026, Iraqi Government Payroll
"""Live bench smoke checks for the Phase 3 governance / locking workflow.

Run each as a single process via `bench execute` (NOT `bench console`):

    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.governance
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.locking
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.api
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.create

Why `bench execute`: each check runs in one process with a proper Frappe context,
so the first failed assertion raises, aborts the run with a non-zero exit code,
and the "PASSED" line — the last statement of each function — is unreachable once
anything has failed. The old `bench console < script.py` harness executed line by
line: it swallowed per-line exceptions (printing a false "PASSED") and tripped a
document-lock race during calculate. These functions only build/read records and
drive the governance API; they contain no calculation, governance or DocType logic.
"""

import frappe


def _blocked(fn):
	"""Return True if calling fn() raises (i.e. the action was blocked)."""
	try:
		fn()
		return False
	except Exception:
		return True


def governance():
	"""Phase 3 M1 — approval path + protection rules + M5 audit-event trail."""
	# Reuse / create a valid employee profile (Bachelor g7s1 -> 0 calc errors)
	if not frappe.db.exists("Government Employee Payroll Profile", {"employee_number": "E1"}):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": "E1", "employee_name": "Smoke Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
		}).insert()

	if not frappe.db.exists("Payroll Period", {"year": 2020, "month": 6}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2020, "month": 6,
						"start_date": "2020-06-01", "end_date": "2020-06-30", "status": "Open"}).insert()
	period = frappe.get_value("Payroll Period", {"year": 2020, "month": 6}, "name")

	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "All"}).insert()
	print("after insert        :", run.workflow_state)            # Draft

	run.calculate_run(); run.reload()
	print("after calculate     :", run.workflow_state, "| run_status:", run.run_status,
		  "| errors:", run.error_count, "| calculated_by:", run.calculated_by)
	assert run.workflow_state == "Calculated", run.workflow_state

	run.submit_for_review(); run.reload()
	print("after submit_review :", run.workflow_state, "| reviewed_by:", run.reviewed_by)
	assert run.workflow_state == "Under Review", run.workflow_state

	run.approve_run(); run.reload()
	print("after approve       :", run.workflow_state, "| approved_by:", run.approved_by)
	assert run.workflow_state == "Approved", run.workflow_state

	# Protection rule: cannot recalculate after approval
	recalc_blocked = _blocked(lambda: run.calculate_run())
	print("recalc blocked      :", recalc_blocked)
	assert recalc_blocked, "recalculation allowed after approval"

	run.submit_run(); run.reload()
	print("after submit        :", run.workflow_state, "| submitted_by:", run.submitted_by)
	assert run.workflow_state == "Submitted", run.workflow_state

	# Protection rule: cannot delete a submitted run
	delete_blocked = _blocked(lambda: frappe.delete_doc("Payroll Run", run.name))
	print("delete blocked      :", delete_blocked)
	assert delete_blocked, "delete allowed on submitted run"

	# M5: every transition left exactly one immutable governance event, in order.
	events = frappe.get_all("Payroll Run Governance Event",
							filters={"payroll_run": run.name},
							fields=["action", "from_state", "to_state"],
							order_by="creation asc")
	actions = [e["action"] for e in events]
	print("governance events   :", actions)
	assert actions == ["calculate", "submit_for_review", "approve", "submit"], actions

	frappe.db.commit()
	print("\nGOVERNANCE SMOKE TEST PASSED")


def locking():
	"""Phase 3 M3 / M3.1 — lock, historical integrity, retroactive protection."""
	from iraqi_government_payroll.services.lifecycle import lifecycle_service as lc
	from iraqi_government_payroll.services.historical import history_service as hist

	EMP = "LOCK1"
	if not frappe.db.exists("Government Employee Payroll Profile", EMP):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": EMP, "employee_name": "Lock Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
			"employment_status": "Active",
		}).insert()

	period = frappe.db.get_value("Payroll Period", {"year": 2026, "month": 1})
	if not period:
		period = frappe.get_doc({"doctype": "Payroll Period", "year": 2026, "month": 1,
								 "start_date": "2026-01-01", "end_date": "2026-01-31",
								 "status": "Open"}).insert().name

	# Run -> approve -> submit -> lock
	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "Employee",
						  "scope_reference": EMP}).insert()
	run.calculate_run(); run.reload()
	# The run builds DRAFT slips; submitting one fires Salary Slip.on_submit, which
	# writes the immutable Payroll Calculation Snapshot the historical-integrity
	# checks below read back. (Governance run state is independent of slip docstatus.)
	slip = frappe.db.get_value(
		"Salary Slip", {"payroll_run": run.name, "employee_profile": EMP}, "name")
	assert slip, "run did not produce a Salary Slip for the employee"
	slip_doc = frappe.get_doc("Salary Slip", slip)
	if slip_doc.docstatus == 0:
		slip_doc.submit()
	run.submit_for_review(); run.reload()
	run.approve_run(); run.reload()
	run.submit_run(); run.reload()
	run.lock_run(); run.reload()
	print("workflow_state      :", run.workflow_state, "| locked_by:", run.locked_by)
	assert run.workflow_state == "Locked", run.workflow_state
	assert run.is_run_locked() and run.is_historical_period()

	net_before = hist.get_payroll_snapshot(run.name, EMP)["net_amount"]
	print("historical net      :", net_before)

	# Post-lock (future-dated) change is allowed; profile mutated to simulate promotion
	lc.transfer_employee(EMP, "2026-06-01", to_entity=None, reason="post-lock transfer")
	prof = frappe.get_doc("Government Employee Payroll Profile", EMP)
	prof.current_stage = 5
	prof.save()
	print("profile changed     : stage ->",
		  frappe.db.get_value("Government Employee Payroll Profile", EMP, "current_stage"))

	# Retroactive change INTO the locked period must be blocked
	retro_blocked = _blocked(lambda: lc.transfer_employee(EMP, "2026-01-15", reason="retroactive"))
	print("retroactive blocked :", retro_blocked)
	assert retro_blocked, "retroactive transfer into locked period was allowed"

	# Historical snapshot unchanged
	net_after = hist.get_payroll_snapshot(run.name, EMP)["net_amount"]
	print("historical net after:", net_after)
	assert net_after == net_before, "locked payroll snapshot changed!"

	# Recalculation must be blocked
	recalc_blocked = _blocked(lambda: run.calculate_run())
	print("recalc blocked      :", recalc_blocked)
	assert recalc_blocked, "recalculation allowed after lock"

	# Deletion must be blocked
	delete_blocked = _blocked(lambda: frappe.delete_doc("Payroll Run", run.name))
	print("delete blocked      :", delete_blocked)
	assert delete_blocked, "delete allowed after lock"

	frappe.db.commit()
	print("\nPAYROLL LOCKING SMOKE TEST PASSED")


def api():
	"""Phase 3 M6 — the governance REST surface (api.payroll_api) end to end.

	Drives a run through get_run_governance + run_governance_action and checks that
	state, available actions and the M5 audit trail flow through the API exactly as
	through the controller. Runs as Administrator (System Manager bypasses roles).
	"""
	from iraqi_government_payroll.api import payroll_api as papi

	if not frappe.db.exists("Government Employee Payroll Profile", {"employee_number": "E1"}):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": "E1", "employee_name": "Smoke Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
		}).insert()
	if not frappe.db.exists("Payroll Period", {"year": 2020, "month": 6}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2020, "month": 6,
						"start_date": "2020-06-01", "end_date": "2020-06-30", "status": "Open"}).insert()
	period = frappe.get_value("Payroll Period", {"year": 2020, "month": 6}, "name")

	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "All"}).insert()

	g0 = papi.get_run_governance(run.name)
	print("initial state       :", g0["workflow_state"], "| actions:", g0["allowed_actions"])
	assert g0["workflow_state"] == "Draft", g0["workflow_state"]
	assert "calculate" in g0["allowed_actions"]

	r1 = papi.run_governance_action(run.name, "calculate")
	print("after calculate     :", r1["workflow_state"], "| actions:", r1["allowed_actions"])
	assert r1["workflow_state"] == "Calculated", r1["workflow_state"]
	assert "submit_for_review" in r1["allowed_actions"]

	papi.run_governance_action(run.name, "submit_for_review")
	papi.run_governance_action(run.name, "approve")
	r2 = papi.run_governance_action(run.name, "submit")
	print("after submit        :", r2["workflow_state"], "| actions:", r2["allowed_actions"])
	assert r2["workflow_state"] == "Submitted", r2["workflow_state"]

	# Unknown action is rejected before any dispatch
	bad = _blocked(lambda: papi.run_governance_action(run.name, "nuke"))
	print("unknown rejected    :", bad)
	assert bad, "unknown action was not rejected"

	# The same immutable M5 audit trail is visible through the read endpoint
	g1 = papi.get_run_governance(run.name)
	logged = [e["action"] for e in g1["events"]]
	print("events via API      :", logged)
	assert logged == ["calculate", "submit_for_review", "approve", "submit"], logged

	frappe.db.commit()
	print("\nGOVERNANCE API SMOKE TEST PASSED")


def create():
	"""Phase 3 M8 — the create_payroll_run endpoint: validation + duplicate guard.

	Uses a dedicated period (2019/12) that no other check touches, and rolls back
	the created run at the end so the check is re-runnable and never collides with
	the duplicate guard on a later run.
	"""
	from iraqi_government_payroll.api import payroll_api as papi

	if not frappe.db.exists("Payroll Period", {"year": 2019, "month": 12}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2019, "month": 12,
						"start_date": "2019-12-01", "end_date": "2019-12-31",
						"status": "Open"}).insert()
		frappe.db.commit()                      # keep the period; only the run is rolled back
	period = frappe.get_value("Payroll Period", {"year": 2019, "month": 12}, "name")

	r = papi.create_payroll_run(period, "IRAQ-2015", "All", None)
	print("created run          :", r["name"], "|", r["workflow_state"], "| actions:", r["allowed_actions"])
	assert r["workflow_state"] == "Draft", r["workflow_state"]
	assert "calculate" in r["allowed_actions"]

	# Duplicate (same period + rule_set + scope, not cancelled) is blocked
	dup_blocked = _blocked(lambda: papi.create_payroll_run(period, "IRAQ-2015", "All", None))
	print("duplicate blocked    :", dup_blocked)
	assert dup_blocked, "duplicate active run was allowed"

	# Invalid inputs are rejected
	bad_period = _blocked(lambda: papi.create_payroll_run("NO-SUCH-PERIOD", "IRAQ-2015", "All", None))
	print("bad period rejected  :", bad_period)
	assert bad_period, "non-existent period was accepted"

	missing_ref = _blocked(lambda: papi.create_payroll_run(period, "IRAQ-2015", "Employee", None))
	print("missing ref rejected :", missing_ref)
	assert missing_ref, "Employee scope without a reference was accepted"

	frappe.db.rollback()                        # discard the created run; re-runnable
	print("\nPAYROLL RUN CREATE SMOKE TEST PASSED")
