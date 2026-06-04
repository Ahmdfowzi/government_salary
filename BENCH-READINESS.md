# Bench Readiness — Iraqi Government Payroll

How to install and verify the `iraqi_government_payroll` Frappe app on a real
bench. Everything below has been validated **structurally** (JSON schema, Python
imports, pure unit/integration tests) but **not yet on a live bench** — see the
caveat at the bottom.

---

## 1. Prerequisites
- Python 3.10+
- Node 18+ and Yarn (for Frappe assets)
- **MariaDB** 10.6+ (or compatible) running
- **Redis** (cache + queue)
- `wkhtmltopdf` (for PDF print formats)
- Frappe Bench CLI (`pip install frappe-bench`) and an initialized bench (`bench init`)
- A Frappe site (`bench new-site <site>`)

> `Currency` is a Frappe **framework** DocType, so ERPNext is **not** required.

## 2. Install commands
```bash
# from the bench directory
bench get-app iraqi_government_payroll /path/to/iraqi-government-payroll/backend/iraqi_government_payroll
bench --site <site> install-app iraqi_government_payroll
bench --site <site> migrate
```
`migrate` syncs the 27 DocTypes and imports the fixtures (Roles + the IRAQ-2015
rule set and its members) declared in `hooks.py`.

## 3. Bench readiness checklist
| # | Step | Command | Expected result |
|---|------|---------|-----------------|
| 1 | Get app | `bench get-app …` | App copied into `apps/`, added to `apps.txt` |
| 2 | Install app | `bench --site <site> install-app iraqi_government_payroll` | App installed, no errors |
| 3 | Migrate | `bench --site <site> migrate` | 27 DocTypes created; fixtures imported |
| 4 | Fixture import | (part of migrate) | Rule set `IRAQ-2015` (Active) + `IRAQ-2008` (Archived); 143 scale rows; 16 qualification rules; 4 tax brackets; 9 promotion durations |
| 5 | Role fixtures | `bench --site <site> console` → `frappe.get_all("Role", filters={"role_name":["in",["Payroll Administrator","Payroll Manager","Payroll Officer","HR User","Finance User","Auditor"]]})` | 6 roles present |
| 6 | DocType creation | `frappe.db.count("DocType", {"module":"Government Payroll"})` | 27 |
| 7 | Counts | `frappe.db.count("Government Salary Scale Detail")` etc. | scale detail 143 · Income Tax Bracket 4 · Qualification Appointment Rule 16 · Promotion Grade Duration 9 |
| 8 | Sample Salary Slip | create a profile + `Salary Slip` (employee_profile, payroll_period), save | fields auto-populate (basic/gross/deductions/net); submit → one immutable snapshot |
| 9 | Sample Payroll Run | create `Payroll Run` (period + rule_set) → call `run_batch()` | draft slips created for Active profiles; run_status `Completed With Warnings`; counts populated |

### Sample console snippet (steps 8–9)
```python
# bench --site <site> console
import frappe
# minimal profile
p = frappe.get_doc({"doctype":"Government Employee Payroll Profile",
    "employee_number":"E1","employee_name":"Test","rule_set":"IRAQ-2015",
    "grade_code":"7","current_grade":7,"current_stage":1,"qualification":"Bachelor",
    "status":"Active"}).insert()
period = frappe.get_doc({"doctype":"Payroll Period","year":2020,"month":6,
    "start_date":"2020-06-01","end_date":"2020-06-30","status":"Open"}).insert()
slip = frappe.get_doc({"doctype":"Salary Slip","employee_profile":p.name,
    "payroll_period":period.name}).insert()
print(slip.basic_salary, slip.total_earnings, slip.total_deductions, slip.net_salary)
# expect: 296000 429200 57713 371487   (PC-6 pending -> no pension deduction)
run = frappe.get_doc({"doctype":"Payroll Run","payroll_period":period.name,
    "rule_set":"IRAQ-2015","scope":"All"}).insert()
print(run.run_batch())
```

## 4. Troubleshooting
| Symptom | Likely cause | Fix |
|---|---|---|
| `migrate` fails on a Link to `Currency` | Site missing the framework `Currency` doctype (very old Frappe) | Upgrade Frappe, or change `currency`/`default_currency` Links to Data |
| Fixtures not imported | `hooks.fixtures` order or filename mismatch | Ensure fixture files are named `frappe.scrub(doctype).json`; rule set must import before its members |
| `Select … is not a valid value` on import | A fixture value outside a Select's options | Confirm vocabularies (grade_code, match_key, qualification_level) match the DocType options |
| Salary Slip saves but fields blank | Engine not wired / import error | Check `iraqi_government_payroll.services.payroll_engine.repository` imports cleanly |
| Tax = 0 unexpectedly / pension missing | PC-6/PC-7 pending (provisional) | Expected — see Known PC limitations in `ENGINE-BOUNDARIES.md` |
| Tree (Government Entity) errors | NestedSet rebuild | `bench --site <site> execute frappe.utils.nestedset.rebuild_tree` for `Government Entity` |

## 5. Run the test suite (no bench required)
```bash
cd backend/iraqi_government_payroll/iraqi_government_payroll/tests
python3 -m unittest discover -p "test_*.py" -v
```

## 6. Known caveat (this machine)
The development machine used to build this project has **no Frappe bench,
MariaDB, or Redis installed**. All milestones (M1–M8) were therefore verified by
**structural validation + pure unit/integration tests against the fixtures**, not
by a live `bench migrate`. The live install round-trip (steps 1–9 above) is the
one remaining verification and should be run on a provisioned bench before
production use.
