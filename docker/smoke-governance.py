# Payroll Run governance smoke test (Phase 3 M1).
# Run INSIDE the frappe container:
#   docker compose -f docker/docker-compose.yml exec frappe \
#     bash -lc "cd ~/frappe-bench && bench --site payroll.localhost console < /mnt/scripts/smoke-governance.py"
import frappe

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
assert run.workflow_state == "Calculated"

run.submit_for_review(); run.reload()
print("after submit_review :", run.workflow_state, "| reviewed_by:", run.reviewed_by)
assert run.workflow_state == "Under Review"

run.approve_run(); run.reload()
print("after approve       :", run.workflow_state, "| approved_by:", run.approved_by)
assert run.workflow_state == "Approved"

# Protection rule: cannot recalculate after approval
try:
    run.calculate_run()
    raise SystemExit("FAIL: recalculation allowed after approval")
except frappe.ValidationError as e:
    print("recalc blocked      :", str(e)[:70])
except Exception as e:
    print("recalc blocked      :", str(e)[:70])

run.submit_run(); run.reload()
print("after submit         :", run.workflow_state, "| submitted_by:", run.submitted_by)
assert run.workflow_state == "Submitted"

# Protection rule: cannot delete a submitted run
try:
    frappe.delete_doc("Payroll Run", run.name)
    raise SystemExit("FAIL: delete allowed on submitted run")
except Exception as e:
    print("delete blocked      :", str(e)[:70])

frappe.db.commit()
print("\nGOVERNANCE SMOKE TEST PASSED")
