# Employee lifecycle smoke test (Phase 3 M2).
# Run INSIDE the frappe container:
#   docker compose -f docker/docker-compose.yml exec frappe \
#     bash -lc "cd ~/frappe-bench && bench --site payroll.localhost console < /mnt/scripts/smoke-lifecycle.py"
import frappe
from iraqi_government_payroll.services.lifecycle import lifecycle_service as lc

EMP = "LC1"

# Clean prior run (lifecycle records block delete, so allow ignore_permissions cleanup)
if frappe.db.exists("Government Employee Payroll Profile", EMP):
    print("note: profile", EMP, "already exists; reusing")
else:
    frappe.get_doc({
        "doctype": "Government Employee Payroll Profile",
        "employee_number": EMP, "employee_name": "Lifecycle Test",
        "rule_set": "IRAQ-2015", "grade_code": "7", "current_grade": 7,
        "current_stage": 1, "qualification": "Bachelor", "status": "Active",
    }).insert()

def state():
    p = frappe.get_doc("Government Employee Payroll Profile", EMP)
    return p.employment_status, p.current_entity, p.last_lifecycle_event

# Appointment
lc.appoint_employee(EMP, "2010-01-01", entity=None, position=None,
                    qualification="Bachelor", grade_code="7", stage=1, rule_set="IRAQ-2015")
print("after appoint  :", state())
assert state()[0] == "Active"

# Transfer
lc.transfer_employee(EMP, "2015-06-01", from_entity=None, to_entity=None, reason="reorg")
print("after transfer :", state())
assert state()[0] == "Active"

# Leave Without Salary
leave = lc.start_leave_without_salary(EMP, "2018-03-01", end_date="2019-02-28", reason="study")
print("after leave    :", state())
assert state()[0] == "On Leave Without Salary"

# Payroll exclusion while on leave
run = frappe.get_doc({"doctype": "Payroll Run", "rule_set": "IRAQ-2015", "scope": "Employee",
                      "scope_reference": EMP,
                      "payroll_period": frappe.db.get_value("Payroll Period", {"year": 2020, "month": 6})
                      or frappe.get_doc({"doctype": "Payroll Period", "year": 2020, "month": 6,
                                         "start_date": "2020-06-01", "end_date": "2020-06-30",
                                         "status": "Open"}).insert().name}).insert()
run.calculate_run(); run.reload()
print("payroll while on leave -> total_employees:", run.total_employees)
assert run.total_employees == 0, "on-leave employee must be excluded from payroll"

# Return To Service
lc.return_to_service(EMP, "2019-03-01", linked_leave=leave)
print("after return   :", state())
assert state()[0] == "Active"

# Retirement
lc.retire_employee(EMP, "2020-12-31", reason="age")
print("after retire   :", state())
assert state()[0] == "Retired"

frappe.db.commit()
print("\nLIFECYCLE SMOKE TEST PASSED")
