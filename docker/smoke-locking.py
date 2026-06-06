# Payroll locking & historical integrity smoke test (Phase 3 M3 / M3.1).
# Run INSIDE the frappe container:
#   docker compose -f docker/docker-compose.yml exec frappe \
#     bash -lc "cd ~/frappe-bench && bench --site payroll.localhost console < /mnt/scripts/smoke-locking.py"
#
# Wrapped in main(): the success line is the LAST statement of main and only runs
# if every assertion passed, so it can never print after a failure (even under
# the line-by-line `bench console`).
import frappe
from iraqi_government_payroll.services.lifecycle import lifecycle_service as lc
from iraqi_government_payroll.services.historical import history_service as hist

EMP = "LOCK1"


def _blocked(fn):
	"""Return True if calling fn() raises (i.e. the action was blocked)."""
	try:
		fn()
		return False
	except Exception:
		return True


def main():
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
	run.submit_for_review(); run.reload()
	run.approve_run(); run.reload()
	run.submit_run(); run.reload()
	run.lock_run(); run.reload()
	print("workflow_state      :", run.workflow_state, "| locked_by:", run.locked_by)
	assert run.workflow_state == "Locked", run.workflow_state
	assert run.is_locked() and run.is_historical_period()

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


main()
