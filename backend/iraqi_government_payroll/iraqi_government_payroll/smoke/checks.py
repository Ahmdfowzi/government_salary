# Copyright (c) 2026, Iraqi Government Payroll
"""Live bench smoke checks for the Phase 3 governance / locking workflow.

Run each as a single process via `bench execute` (NOT `bench console`):

    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.governance
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.locking
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.api
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.create
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.reports
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.pension_report
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.bank_transfer
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.excel_export
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.pdf_export
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.accounting_journal
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.security
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.grade_validation
    bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.demo

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


def reports():
	"""Phase 4 M10 — the read-only report endpoints reconcile to the Salary Slip.

	Builds a one-employee run (dedicated employee + period), calculates it (draft
	slips), reads all five reports and checks every total ties back to the slip,
	then rolls back so the check is re-runnable.
	"""
	from iraqi_government_payroll.api import reports_api as rep

	EMP = "REP1"
	if not frappe.db.exists("Government Employee Payroll Profile", EMP):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": EMP, "employee_name": "Report Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
			"employment_status": "Active",
		}).insert()
		frappe.db.commit()                      # keep the profile; only the run is rolled back

	if not frappe.db.exists("Payroll Period", {"year": 2018, "month": 6}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2018, "month": 6,
						"start_date": "2018-06-01", "end_date": "2018-06-30",
						"status": "Open"}).insert()
		frappe.db.commit()
	period = frappe.get_value("Payroll Period", {"year": 2018, "month": 6}, "name")

	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "Employee",
						  "scope_reference": EMP}).insert()
	run.calculate_run(); run.reload()

	summary = rep.run_summary(run.name)
	emp = rep.employee_register(run.name)
	allow = rep.allowances_register(run.name)
	ded = rep.deductions_register(run.name)
	tax = rep.tax_register(run.name)
	print("summary             :", summary)
	print("employee rows       :", emp["rows"])

	assert summary["employees"] == 1, summary
	assert len(emp["rows"]) == 1
	row = emp["rows"][0]
	# reconcile registers back to the slip totals (the single source)
	assert emp["totals"]["net"] == summary["total_net"], "net mismatch"
	assert allow["grand_total"] == emp["totals"]["allowances"], "allowances mismatch"
	assert ded["grand_total"] == emp["totals"]["deductions"], "deductions mismatch"
	assert tax["total_tax"] <= ded["grand_total"], "tax exceeds deductions"
	assert row["basic"] + row["allowances"] == summary["total_earnings"], "earnings mismatch"
	print("reconciled          : net/allowances/deductions/tax all tie to the slip")

	frappe.db.rollback()                        # discard the run; re-runnable
	print("\nPAYROLL REPORTS SMOKE TEST PASSED")


def pension_report():
	"""Phase 4 M11 — the Retirement Pension Register reads stored Pension
	Calculation values and reconciles. Inserts one sample record (no retirement
	calc here — figures are supplied as already-computed), reads the register,
	checks reconciliation, then rolls back.
	"""
	from iraqi_government_payroll.api import reports_api as rep

	if not frappe.db.exists("Government Employee Payroll Profile", "PEN1"):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": "PEN1", "employee_name": "Pension Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
			"employment_status": "Retired",
		}).insert()
		frappe.db.commit()

	# Stored, already-computed pension figures (gross = approved + cert + col;
	# net = gross - tax - other). NOT computed here.
	approved, cert, col, tax, other, eos = 909000, 90900, 227250, 60000, 0, 12360000
	gross = approved + cert + col
	net = gross - tax - other
	frappe.get_doc({
		"doctype": "Pension Calculation", "employee_profile": "PEN1",
		"employee_name": "Pension Test", "rule_set": "IRAQ-2015",
		"calculation_date": "2026-06-15", "period_date": "2026-06-01", "status": "Calculated",
		"service_years": 36, "average_36_months": 1010000, "accrual_rate": 2.5,
		"approved_pension": approved, "certificate_allowance": cert, "cost_of_living": col,
		"gross_pension": gross, "monthly_tax": tax, "other_deductions": other,
		"net_pension": net, "end_of_service_bonus": eos,
	}).insert()

	reg = rep.pension_register("2026-06-01", "2026-06-30", None)
	print("pension rows        :", reg["rows"])
	print("pension totals      :", reg["totals"])
	assert reg["count"] == 1, reg["count"]
	row = reg["rows"][0]
	assert row["qualification"] == "Bachelor", row["qualification"]
	assert row["net_pension"] == net
	# reconciliation against stored figures (no recompute)
	assert row["gross_pension"] == row["approved_pension"] + row["certificate_allowance"] \
		+ row["cost_of_living"], "gross mismatch"
	assert row["net_pension"] == row["gross_pension"] - row["monthly_tax"] \
		- row["other_deductions"], "net mismatch"
	assert reg["totals"]["net_pension"] == net
	print("reconciled          : gross/net tie to stored pension figures")

	frappe.db.rollback()                        # discard the record; re-runnable
	print("\nRETIREMENT PENSION REGISTER SMOKE TEST PASSED")


def bank_transfer():
	"""Phase 4 M12 — Bank Transfer Export: net from the slip, bank from the profile,
	missing bank data flagged (never skipped). One employee has bank details, one
	does not; both appear. Rolls back so it is re-runnable.
	"""
	from iraqi_government_payroll.api import reports_api as rep

	# BANKED employee (has an account) and UNBANKED employee (no account/iban).
	for emp, name, acct in (("BANK1", "Banked", "1122334455"), ("BANK2", "Unbanked", None)):
		if not frappe.db.exists("Government Employee Payroll Profile", emp):
			doc = {
				"doctype": "Government Employee Payroll Profile",
				"employee_number": emp, "employee_name": name,
				"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
				"current_stage": 1, "qualification": "Bachelor", "status": "Active",
				"employment_status": "Active",
			}
			if acct:
				doc["bank_account"] = acct
				doc["bank_name"] = "Rafidain"
			frappe.get_doc(doc).insert()
			frappe.db.commit()

	if not frappe.db.exists("Payroll Period", {"year": 2017, "month": 6}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2017, "month": 6,
						"start_date": "2017-06-01", "end_date": "2017-06-30",
						"status": "Open"}).insert()
		frappe.db.commit()
	period = frappe.get_value("Payroll Period", {"year": 2017, "month": 6}, "name")

	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "All"}).insert()
	run.calculate_run(); run.reload()

	bt = rep.bank_transfer(run.name)
	print("bank rows           :", bt["rows"])
	print("incomplete_count    :", bt["incomplete_count"], "| total_net:", bt["total_net"])

	by = {r["employee_profile"]: r for r in bt["rows"]}
	assert "BANK1" in by and "BANK2" in by, "an employee row was skipped"   # nothing skipped
	assert by["BANK1"]["bank_complete"] is True, by["BANK1"]
	assert by["BANK1"]["bank_account"] == "1122334455"
	assert by["BANK2"]["bank_complete"] is False, by["BANK2"]
	assert "bank_account" in by["BANK2"]["missing"], by["BANK2"]["missing"]
	# net is read from the slip (positive for the banked active employee)
	assert by["BANK1"]["net"] > 0
	# total_net is the plain sum of slip nets (no recompute)
	assert bt["total_net"] == sum(r["net"] for r in bt["rows"])
	print("flagged             : BANK2 missing bank_account, included not skipped")

	frappe.db.rollback()                        # discard the run; re-runnable
	print("\nBANK TRANSFER SMOKE TEST PASSED")


def excel_export():
	"""Phase 4 M13 — Excel export renders a valid workbook for every report by
	reusing the report aggregators. Builds a run + a pension record, renders each
	of the 7 reports to xlsx, reopens one and checks the header, then rolls back.
	"""
	import io
	from openpyxl import load_workbook
	from iraqi_government_payroll.api import reports_api as rep

	EMP = "XLS1"
	if not frappe.db.exists("Government Employee Payroll Profile", EMP):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": EMP, "employee_name": "Excel Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
			"employment_status": "Active", "bank_account": "55667788",
		}).insert()
		frappe.db.commit()
	if not frappe.db.exists("Payroll Period", {"year": 2016, "month": 6}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2016, "month": 6,
						"start_date": "2016-06-01", "end_date": "2016-06-30",
						"status": "Open"}).insert()
		frappe.db.commit()
	period = frappe.get_value("Payroll Period", {"year": 2016, "month": 6}, "name")

	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "Employee",
						  "scope_reference": EMP}).insert()
	run.calculate_run(); run.reload()

	run_reports = ["run_summary", "employee_register", "allowances_register",
				   "deductions_register", "tax_register", "bank_transfer"]
	for report in run_reports:
		content = rep.render_report_xlsx(report, run=run.name)
		assert content[:2] == b"PK", f"{report}: not an xlsx"
		assert len(content) > 200, f"{report}: workbook too small"
	# pension uses date/status params
	pen = rep.render_report_xlsx("pension_register", from_date="2016-01-01", to_date="2016-12-31")
	assert pen[:2] == b"PK", "pension: not an xlsx"
	print("rendered            : 7 reports -> valid xlsx")

	# reopen the employee register and check the Arabic header + a totals row
	ws = load_workbook(io.BytesIO(rep.render_report_xlsx("employee_register", run=run.name))).active
	assert ws.cell(row=1, column=1).value == "الموظف", ws.cell(row=1, column=1).value
	assert ws.sheet_view.rightToLeft, "sheet not RTL"
	assert ws.cell(row=ws.max_row, column=1).value == "الإجمالي", "no totals row"
	print("reopened            : header الموظف, RTL, totals row present")

	frappe.db.rollback()                        # discard the run; re-runnable
	print("\nEXCEL EXPORT SMOKE TEST PASSED")


def pdf_export():
	"""Phase 4 M14 — PDF export renders a real (wkhtmltopdf) PDF for every report,
	with bundled Arabic font. Builds a one-employee run, renders each of the 7
	reports to PDF bytes, plus an EMPTY report (no records) still yields a valid
	PDF, then rolls back.
	"""
	from iraqi_government_payroll.api import reports_api as rep

	EMP = "PDF1"
	if not frappe.db.exists("Government Employee Payroll Profile", EMP):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": EMP, "employee_name": "PDF Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
			"employment_status": "Active", "bank_account": "99001122",
		}).insert()
		frappe.db.commit()
	if not frappe.db.exists("Payroll Period", {"year": 2015, "month": 6}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2015, "month": 6,
						"start_date": "2015-06-01", "end_date": "2015-06-30",
						"status": "Open"}).insert()
		frappe.db.commit()
	period = frappe.get_value("Payroll Period", {"year": 2015, "month": 6}, "name")

	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "Employee",
						  "scope_reference": EMP}).insert()
	run.calculate_run(); run.reload()

	run_reports = ["run_summary", "employee_register", "allowances_register",
				   "deductions_register", "tax_register", "bank_transfer"]
	for report in run_reports:
		pdf = rep.render_report_pdf(report, run=run.name)
		assert pdf[:5] == b"%PDF-", f"{report}: not a PDF"
		assert len(pdf) > 1000, f"{report}: PDF too small ({len(pdf)})"
	pen = rep.render_report_pdf("pension_register", from_date="2015-01-01", to_date="2015-12-31")
	assert pen[:5] == b"%PDF-", "pension: not a PDF"
	print("rendered            : 7 reports -> valid PDF bytes")

	# EMPTY report data still produces a valid PDF (no records in this range)
	empty = rep.render_report_pdf("pension_register", from_date="1990-01-01", to_date="1990-12-31")
	assert empty[:5] == b"%PDF-", "empty: not a PDF"
	assert len(empty) > 1000, "empty PDF too small"
	print("empty report        : valid PDF (%d bytes)" % len(empty))

	frappe.db.rollback()                        # discard the run; re-runnable
	print("\nPDF EXPORT SMOKE TEST PASSED")


def accounting_journal():
	"""Phase 4 M15 — accounting journal export proposes BALANCED rows, fails safely
	on an incomplete mapping, and stays empty/safe for an empty run. Proposal only —
	no GL Entry / Journal Entry is ever created. Rolls back so it is re-runnable.
	"""
	from iraqi_government_payroll.api import accounting_api as acc

	mapping = {
		"salary_expense_account": "5100", "allowance_expense_account": "5200",
		"employee_payable_account": "2100", "pension_payable_account": "2200",
		"tax_payable_account": "2300", "other_deductions_payable_account": "2400",
	}
	for field, value in mapping.items():
		frappe.db.set_single_value("Payroll Account Mapping", field, value)

	EMP = "JRN1"
	if not frappe.db.exists("Government Employee Payroll Profile", EMP):
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": EMP, "employee_name": "Journal Test",
			"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
			"current_stage": 1, "qualification": "Bachelor", "status": "Active",
			"employment_status": "Active",
		}).insert()
		frappe.db.commit()
	if not frappe.db.exists("Payroll Period", {"year": 2020, "month": 6}):
		frappe.get_doc({"doctype": "Payroll Period", "year": 2020, "month": 6,
						"start_date": "2020-06-01", "end_date": "2020-06-30",
						"status": "Open"}).insert()
		frappe.db.commit()
	period = frappe.get_value("Payroll Period", {"year": 2020, "month": 6}, "name")

	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": "IRAQ-2015", "scope": "Employee",
						  "scope_reference": EMP}).insert()
	run.calculate_run(); run.reload()

	j = acc.journal_export(run.name)
	print("journal rows        :", j["rows"])
	print("debit/credit        :", j["total_debit"], "/", j["total_credit"], "| balanced:", j["balanced"])
	assert j["balanced"] is True, j
	assert j["total_debit"] == j["total_credit"], "debit != credit"
	assert j["total_debit"] > 0, "expected a non-trivial journal"
	descs = [r["description"] for r in j["rows"]]
	assert "Salary Expense" in descs and "Employee Payable" in descs, descs
	# debit and credit each sum independently to the same total
	assert sum(r["debit"] for r in j["rows"]) == sum(r["credit"] for r in j["rows"])

	# Incomplete mapping fails safely (no partial/invalid export)
	frappe.db.set_single_value("Payroll Account Mapping", "employee_payable_account", "")
	failed = _blocked(lambda: acc.journal_export(run.name))
	print("incomplete mapping  : fails =", failed)
	assert failed, "incomplete mapping did not fail"
	frappe.db.set_single_value("Payroll Account Mapping", "employee_payable_account", "2100")

	# Empty run -> safe empty balanced journal (no slips for a non-existent employee)
	empty_run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
								"rule_set": "IRAQ-2015", "scope": "Employee",
								"scope_reference": "NOBODY-XYZ"}).insert()
	empty_run.calculate_run(); empty_run.reload()
	ej = acc.journal_export(empty_run.name)
	print("empty journal       :", ej["rows"], "| balanced:", ej["balanced"])
	assert ej["rows"] == [] and ej["balanced"] and ej["total_debit"] == 0, ej

	frappe.db.rollback()                        # discard everything; no posting, re-runnable
	print("\nACCOUNTING JOURNAL SMOKE TEST PASSED")


def security():
	"""Phase 5 M1 — RBAC: roles exist; Payroll Run permissions enforce read-only
	for Read Only User / Auditor and full for the admin; and the sensitive
	accounting-journal export is denied to Read Only User but allowed to Finance.
	"""
	from iraqi_government_payroll.api import accounting_api as acc

	ROLES = ["Government Payroll Administrator", "HR Officer", "Finance Officer", "Read Only User"]
	for r in ROLES:
		assert frappe.db.exists("Role", r), f"missing role: {r}"
	print("roles exist          :", ROLES)

	perms = {p.role: p for p in frappe.get_meta("Payroll Run").permissions}
	ro, ga, fo, au = (perms["Read Only User"], perms["Government Payroll Administrator"],
					  perms["Finance Officer"], perms["Auditor"])
	assert ro.read and not ro.write and not ro.create and not ro.delete and not (ro.export or 0), \
		"Read Only User is not read-only"
	assert ga.read and ga.write and ga.create and ga.delete, "Government Payroll Administrator not full"
	assert fo.read and fo.export and not fo.write, "Finance Officer permissions wrong"
	assert not au.write and not au.create and not au.delete, "Auditor is not read-only"
	print("Payroll Run perms    : ReadOnly read-only · GovAdmin full · Finance read+export · Auditor read-only")

	def ensure_user(email, roles):
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "send_welcome_email": 0,
							"first_name": email.split("@")[0]}).insert(ignore_permissions=True)
		u = frappe.get_doc("User", email)
		have = {r.role for r in u.roles}
		for r in roles:
			if r not in have:
				u.append("roles", {"role": r})
		u.save(ignore_permissions=True)
		return email

	ro_user = ensure_user("sec_readonly@test.local", ["Read Only User"])
	fin_user = ensure_user("sec_finance@test.local", ["Finance Officer"])
	frappe.db.commit()

	# Live permission layer
	assert frappe.has_permission("Payroll Run", "read", user=ro_user), "Read Only User cannot read"
	assert not frappe.has_permission("Payroll Run", "write", user=ro_user), "Read Only User can WRITE"
	print("Read Only User (live): read=yes write=no")

	# Sensitive-action gate via the real endpoint (set_user)
	frappe.set_user(ro_user)
	ro_denied = _blocked(lambda: acc.journal_export("NO-SUCH-RUN"))
	frappe.set_user("Administrator")
	assert ro_denied, "Read Only User was ALLOWED to export the accounting journal"
	print("journal export gate  : Read Only User denied")

	frappe.set_user(fin_user)
	fin_result = acc.journal_export("NO-SUCH-RUN")     # gate passes; empty run -> balanced
	frappe.set_user("Administrator")
	assert fin_result["balanced"], "Finance Officer export failed"
	print("journal export gate  : Finance Officer allowed (empty balanced)")

	frappe.db.rollback()
	print("\nSECURITY SMOKE TEST PASSED")


def grade_validation():
	"""Phase 5 M4.1 — Government Grade master + scale-placement validation, live.

	Verifies, end to end on the bench:
	  1. the Government Grade master holds the 13 legacy codes (values preserved);
	  2. a profile saved with only grade_code backfills the new grade Link (sync);
	  3. an invalid placement (grade 7 stage 99) is REJECTED at profile save — i.e.
	     before any payroll calculation;
	  4. a promotion changes the employee grade Link (and grade_code mirror) WITHOUT
	     touching Government Position / Current Position (salary source = the scale,
	     not the Position);
	  5. an annual increment changes only the employee-level stage, never the grade.
	Rolls back at the end so it is re-runnable.
	"""
	from iraqi_government_payroll.services.payroll_engine import repository as repo

	# 1. Master preserves the 13 legacy codes exactly.
	master = set(frappe.get_all("Government Grade", pluck="name"))
	expected = {"10", "9", "8", "7", "6", "5", "4", "3", "2", "1",
				"SPECIAL_A", "SPECIAL_B", "SPECIAL_C"}
	print("grade master         :", sorted(master))
	assert master >= expected, f"missing grade codes: {expected - master}"

	# 2. Saving with only grade_code backfills the grade Link (controller sync).
	EMP = "GRD1"
	if frappe.db.exists("Government Employee Payroll Profile", EMP):
		frappe.delete_doc("Government Employee Payroll Profile", EMP, force=True)
	prof = frappe.get_doc({
		"doctype": "Government Employee Payroll Profile",
		"employee_number": EMP, "employee_name": "Grade Test",
		"rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
		"current_stage": 1, "qualification": "Bachelor", "status": "Active",
		"employment_status": "Active",
		"appointment_date": "2000-01-01",
		"current_grade_date": "2000-01-01", "current_stage_date": "2000-01-01",
	}).insert()
	prof.reload()
	print("grade backfilled     : grade=%r grade_code=%r" % (prof.grade, prof.grade_code))
	assert prof.grade == "7", f"grade Link not synced from grade_code: {prof.grade!r}"

	# 3. Invalid placement is rejected at SAVE (before any payroll run).
	prof.current_stage = 99
	rejected = _blocked(lambda: prof.save())
	print("invalid stage 99     : rejected =", rejected)
	assert rejected, "grade 7 stage 99 was accepted — validation did not fire"
	prof.reload()                                # discard the bad in-memory change
	assert prof.current_stage == 1, "profile mutated despite rejected save"

	# Capture Position before promotion (must be untouched by the promotion).
	pos_before = (prof.government_position, prof.current_position)

	# 4. Promotion changes grade WITHOUT Position. Grade 7 -> 6 per the scale.
	preq = frappe.get_doc({
		"doctype": "Promotion Request", "employee_profile": EMP,
		"employee_name": "Grade Test", "approval_status": "Approved",
		"due_date": "2024-01-01",
	}).insert()
	res = repo.apply_promotion(preq)
	prof.reload()
	print("after promotion      : grade=%r grade_code=%r stage=%r (was 7)" %
		  (prof.grade, prof.grade_code, prof.current_stage))
	assert prof.grade != "7", "promotion did not change the grade"
	assert prof.grade == prof.grade_code, "grade Link and grade_code mirror diverged"
	assert frappe.db.exists("Government Grade", prof.grade), "new grade not in master"
	assert (prof.government_position, prof.current_position) == pos_before, \
		"promotion changed Government Position — grade must not derive from Position"
	print("position unchanged   :", pos_before, "(grade driven by scale, not Position)")

	# 5. Increment changes only the employee-level stage, not the grade.
	grade_after_promo = prof.grade
	stage_before = prof.current_stage
	ireq = frappe.get_doc({
		"doctype": "Annual Increment Request", "employee_profile": EMP,
		"employee_name": "Grade Test", "approval_status": "Approved",
		"due_date": "2025-01-01",
	}).insert()
	repo.apply_increment(ireq)
	prof.reload()
	print("after increment      : grade=%r stage=%r (was %r)" %
		  (prof.grade, prof.current_stage, stage_before))
	assert prof.grade == grade_after_promo, "increment changed the grade — it must not"
	assert prof.current_stage == stage_before + 1, "increment did not advance the stage by 1"

	frappe.db.rollback()                         # discard everything; re-runnable
	print("\nGRADE VALIDATION SMOKE TEST PASSED")


def demo():
	"""Phase 5 M4 — seed the demo dataset (idempotent) and verify the dashboard /
	reports / exports return meaningful data. This check COMMITS (the demo data is
	meant to persist for demonstration); re-running is safe (the seed is idempotent).
	"""
	from iraqi_government_payroll.demo import seed
	from iraqi_government_payroll.api import reports_api as rep
	from iraqi_government_payroll.api import accounting_api as acc

	summary = seed.seed_demo()
	print("seed summary        :", summary)

	# Demo structure + employees
	assert summary["entities"] == 4, summary
	emp_total = frappe.db.count("Government Employee Payroll Profile",
								{"employee_number": ["like", "DEMO-EMP-%"]})
	assert emp_total >= 25, f"expected >=25 demo employees, got {emp_total}"

	# Run states: active (Calculated) / completed (Submitted) / locked (Locked)
	states = summary["runs"]["states"]
	assert states["active"] == "Calculated", states
	assert states["completed"] == "Submitted", states
	assert states["locked"] == "Locked", states
	active, locked = summary["runs"]["active"], summary["runs"]["locked"]

	# Reports return non-empty data (active = live slips, locked = snapshots)
	assert len(rep.employee_register(active)["rows"]) == emp_total, "employee register empty"
	assert len(rep.tax_register(active)["rows"]) == emp_total, "tax register empty"
	bt = rep.bank_transfer(active)
	assert len(bt["rows"]) == emp_total and bt["incomplete_count"] > 0, "bank transfer wrong"
	assert len(rep.employee_register(locked)["rows"]) == emp_total, "locked snapshot report empty"

	# Accounting journal (proposal) balances; pension register has rows
	j = acc.journal_export(active)
	assert j["balanced"] and j["total_debit"] == j["total_credit"] and j["total_debit"] > 0, j
	pr = rep.pension_register("2024-01-01", "2024-12-31", None)
	assert pr["count"] >= 5, f"pension register too small: {pr['count']}"

	print("verified            : %d employees, reports non-empty, journal balanced, pension %d"
		  % (emp_total, pr["count"]))
	frappe.db.commit()                          # keep the demo data
	print("\nDEMO DATA SMOKE TEST PASSED")
