# Payroll locking & historical integrity smoke test (Phase 3 M3).
# Run INSIDE the frappe container:
#   docker compose -f docker/docker-compose.yml exec frappe \
#     bash -lc "cd ~/frappe-bench && bench --site payroll.localhost console < /mnt/scripts/smoke-locking.py"
import frappe
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

# 1-5: run -> approve -> submit -> lock
run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
                      "rule_set": "IRAQ-2015", "scope": "Employee", "scope_reference": EMP}).insert()
run.calculate_run(); run.reload()
run.submit_for_review(); run.reload()
run.approve_run(); run.reload()
run.submit_run(); run.reload()
run.lock_run(); run.reload()
print("workflow_state      :", run.workflow_state, "| locked_by:", run.locked_by)
assert run.workflow_state == "Locked"
assert run.is_locked() and run.is_historical_period()

snap_before = hist.get_payroll_snapshot(run.name, EMP)
net_before = snap_before["net_amount"]
print("historical net      :", net_before)

# 6-7: promote / transfer / profile change AFTER the locked period (future-dated) -> allowed
lc.transfer_employee(EMP, "2026-06-01", to_entity=None, reason="post-lock transfer")
prof = frappe.get_doc("Government Employee Payroll Profile", EMP)
prof.current_stage = 5            # simulate a promotion effect on the live profile
prof.save()
print("profile changed     : stage ->", frappe.db.get_value("Government Employee Payroll Profile", EMP, "current_stage"))

# Retroactive change INTO the locked period must be blocked
try:
    lc.transfer_employee(EMP, "2026-01-15", to_entity=None, reason="retroactive")
    raise SystemExit("FAIL: retroactive transfer into locked period was allowed")
except Exception as e:
    print("retroactive blocked :", str(e)[:70])

# Historical snapshot unchanged
snap_after = hist.get_payroll_snapshot(run.name, EMP)
print("historical net after:", snap_after["net_amount"])
assert snap_after["net_amount"] == net_before, "locked payroll snapshot changed!"

# Recalc + delete blocked
try:
    run.calculate_run(); raise SystemExit("FAIL: recalc allowed after lock")
except Exception as e:
    print("recalc blocked      :", str(e)[:70])
try:
    frappe.delete_doc("Payroll Run", run.name); raise SystemExit("FAIL: delete allowed after lock")
except Exception as e:
    print("delete blocked      :", str(e)[:70])

frappe.db.commit()
print("\nPAYROLL LOCKING SMOKE TEST PASSED")
