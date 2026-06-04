# Salary Slip + Payroll Run smoke test (M9 task 5).
# Run INSIDE the frappe container:
#   docker compose -f docker/docker-compose.yml exec frappe \
#     bash -lc "cd ~/frappe-bench && bench --site payroll.localhost console < /mnt/scripts/smoke-test.py"
import frappe

SITE_OK = True

# Sample employee payroll profile (Bachelor, grade 7 stage 1)
if not frappe.db.exists("Government Employee Payroll Profile", {"employee_number": "E1"}):
    frappe.get_doc({
        "doctype": "Government Employee Payroll Profile",
        "employee_number": "E1", "employee_name": "Smoke Test",
        "rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
        "current_stage": 1, "qualification": "Bachelor", "status": "Active",
    }).insert()
profile = frappe.get_value("Government Employee Payroll Profile", {"employee_number": "E1"}, "name")

# Payroll Period
if not frappe.db.exists("Payroll Period", {"year": 2020, "month": 6}):
    frappe.get_doc({"doctype": "Payroll Period", "year": 2020, "month": 6,
                    "start_date": "2020-06-01", "end_date": "2020-06-30", "status": "Open"}).insert()
period = frappe.get_value("Payroll Period", {"year": 2020, "month": 6}, "name")

# Salary Slip draft -> auto-populates via M5 engine
slip = frappe.get_doc({"doctype": "Salary Slip", "employee_profile": profile,
                       "payroll_period": period}).insert()
print("=== SALARY SLIP ===")
print("basic_salary   :", slip.basic_salary, "(expect 296000)")
print("gross_salary   :", slip.total_earnings, "(expect 429200)")
print("total_deduct.  :", slip.total_deductions, "(tax 57713; PC-6 pending so pension 0)")
print("net_salary     :", slip.net_salary, "(expect 371487)")

assert slip.basic_salary == 296000, slip.basic_salary
assert slip.total_earnings == 429200, slip.total_earnings
assert slip.net_salary == 371487, slip.net_salary

# Payroll Run batch
run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
                      "rule_set": "IRAQ-2015", "scope": "All"}).insert()
run.run_batch()
run.reload()
print("=== PAYROLL RUN ===")
print("run_status     :", run.run_status, "(expect Completed With Warnings)")
print("total/processed:", run.total_employees, run.processed_count)
assert run.run_status == "Completed With Warnings", run.run_status

frappe.db.commit()
print("\nSMOKE TEST PASSED")
