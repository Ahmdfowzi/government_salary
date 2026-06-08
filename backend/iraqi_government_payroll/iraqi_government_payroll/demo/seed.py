# Copyright (c) 2026, Iraqi Government Payroll
"""Demo data & UAT seeding (Phase 5 M4) — NOT a fixture, NOT auto-loaded.

Run on demand against a bench:

    bench --site <site> execute iraqi_government_payroll.demo.seed.seed_demo

Creates clearly-marked DEMO data only (entity codes/employee numbers prefixed
`DEMO-`, Arabic names tagged «تجريبي») so it never mixes with production records.
Idempotent: every record is created only if missing, so it is safe to re-run.

It uses the EXISTING engines, governance, and APIs — it changes no payroll / tax /
pension / export / permission logic. Driven as Administrator (System Manager), so
governance role checks are bypassed for the seed only.
"""

import frappe

RULE_SET = "IRAQ-2015"
UNIT = "DEMO-UNIT"

# Government Entity hierarchy: Ministry -> Directorate -> Department -> Unit
ENTITIES = [
	("DEMO-MIN", "وزارة العرض التجريبية", "Ministry", None, 1),
	("DEMO-DIR", "المديرية العامة (تجريبي)", "Directorate", "DEMO-MIN", 1),
	("DEMO-DEPT", "قسم الرواتب (تجريبي)", "Department", "DEMO-DIR", 1),
	("DEMO-UNIT", "وحدة الموظفين (تجريبي)", "Unit", "DEMO-DEPT", 0),
]

FIRST_NAMES = ["محمد", "علي", "حسن", "حسين", "أحمد", "زينب", "فاطمة", "عمر",
			   "يوسف", "خالد", "سارة", "نور", "إبراهيم", "مريم", "عبد الله"]
LAST_NAMES = ["العبيدي", "الجبوري", "الكاظمي", "التميمي", "الدليمي", "الموسوي"]
QUALS = ["Bachelor", "Master", "Diploma", "Higher Diploma", "Doctorate", "Secondary"]
GRADES = ["7", "6", "5", "8", "4", "9", "3", "10"]

N_EMP = 30


def _commit():
	frappe.db.commit()


# --------------------------- entities --------------------------- #
def _seed_entities():
	for code, name, etype, parent, is_group in ENTITIES:
		if not frappe.db.exists("Government Entity", code):
			frappe.get_doc({
				"doctype": "Government Entity", "entity_code": code,
				"entity_name_ar": name, "entity_type": etype,
				"parent_government_entity": parent, "is_group": is_group,
			}).insert(ignore_permissions=True)
	_commit()


def _seed_account_mapping():
	# Configure the proposal-only journal mapping so the accounting export works.
	mapping = {
		"salary_expense_account": "5100 - رواتب أساسية",
		"allowance_expense_account": "5200 - مخصصات",
		"employee_payable_account": "2100 - مستحقات الموظفين",
		"pension_payable_account": "2200 - استقطاع التقاعد",
		"tax_payable_account": "2300 - ضريبة الدخل",
		"other_deductions_payable_account": "2400 - استقطاعات أخرى",
	}
	for field, value in mapping.items():
		frappe.db.set_single_value("Payroll Account Mapping", field, value)
	_commit()


# --------------------------- employees --------------------------- #
def _emp_number(i):
	return f"DEMO-EMP-{i:03d}"


def _seed_employees():
	created = 0
	for i in range(1, N_EMP + 1):
		num = _emp_number(i)
		if frappe.db.exists("Government Employee Payroll Profile", num):
			continue
		grade = GRADES[i % len(GRADES)]
		stage = (i % 10) + 1
		qual = QUALS[i % len(QUALS)]
		name = f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {LAST_NAMES[i % len(LAST_NAMES)]} (تجريبي)"
		appoint_year = 1990 + (i % 30)              # spreads service 5..35 years
		bank = "" if i % 7 == 0 else f"IQDEMO{1000 + i}"   # ~1/7 have no account
		frappe.get_doc({
			"doctype": "Government Employee Payroll Profile",
			"employee_number": num, "employee_name": name,
			"rule_set": RULE_SET, "grade": grade, "grade_code": grade, "current_grade": int(grade),
			"current_stage": stage, "qualification": qual,
			"status": "Active", "employment_status": "Active",
			"government_entity": UNIT, "current_entity": UNIT,
			"appointment_date": f"{appoint_year}-01-15",
			"bank_account": bank,
			"bank_name": "مصرف الرافدين" if bank else "",
			"iban": f"IQ98RAFI{2000 + i:08d}" if bank else "",
			"national_id": f"199{i:09d}",
		}).insert(ignore_permissions=True)
		created += 1
	_commit()
	return created


# --------------------------- payroll runs --------------------------- #
def _make_run(year, month):
	"""Create + calculate a Government-Entity-scoped run for the demo unit."""
	if not frappe.db.exists("Payroll Period", {"year": year, "month": month}):
		frappe.get_doc({"doctype": "Payroll Period", "year": year, "month": month,
						"start_date": f"{year}-{month:02d}-01", "end_date": f"{year}-{month:02d}-28",
						"status": "Open"}).insert(ignore_permissions=True)
	period = frappe.get_value("Payroll Period", {"year": year, "month": month}, "name")
	existing = frappe.db.exists("Payroll Run", {"payroll_period": period, "scope_reference": UNIT})
	if existing:
		return frappe.get_doc("Payroll Run", existing)
	run = frappe.get_doc({"doctype": "Payroll Run", "payroll_period": period,
						  "rule_set": RULE_SET, "scope": "Government Entity",
						  "scope_reference": UNIT}).insert(ignore_permissions=True)
	run.calculate_run(); run.reload()
	return run


def _advance(run, *steps):
	for step in steps:
		getattr(run, step)(); run.reload()


def _seed_runs():
	states = {}
	# Active / unlocked — left at Calculated (in progress).
	active = _make_run(2024, 3)
	states["active"] = active.workflow_state

	# Completed — driven to Submitted.
	completed = _make_run(2024, 2)
	if completed.workflow_state == "Calculated":
		_advance(completed, "submit_for_review", "approve_run", "submit_run")
	states["completed"] = completed.workflow_state

	# Locked — submit the slips (immutable snapshots) then lock.
	locked = _make_run(2024, 1)
	if locked.workflow_state != "Locked":
		for slip in frappe.get_all("Salary Slip",
								   filters={"payroll_run": locked.name, "docstatus": 0},
								   pluck="name"):
			doc = frappe.get_doc("Salary Slip", slip)
			doc.submit()
		if locked.workflow_state == "Calculated":
			_advance(locked, "submit_for_review", "approve_run", "submit_run", "lock_run")
	states["locked"] = locked.workflow_state
	_commit()
	return {"active": active.name, "completed": completed.name, "locked": locked.name,
			"states": states}


# --------------------------- pension / increments / promotions --------------------------- #
def _seed_pensions():
	# guard on a sentinel record
	if frappe.db.exists("Pension Calculation", {"employee_profile": _emp_number(1)}):
		return 0
	cert_by_qual = {"Bachelor": 0, "Master": 60000, "Diploma": 30000,
					"Higher Diploma": 45000, "Doctorate": 120000, "Secondary": 0}
	created = 0
	for k, i in enumerate(range(1, N_EMP + 1, 5)):              # ~6 retirees
		num = _emp_number(i)
		if not frappe.db.exists("Government Employee Payroll Profile", num):
			continue
		prof = frappe.get_doc("Government Employee Payroll Profile", num)
		service_years = 25 + (k * 2)
		approved = 600000 + k * 40000
		cert = cert_by_qual.get(prof.qualification, 0)
		col = 200000
		gross = approved + cert + col
		tax = round(gross * 0.05)
		other = 0
		net = gross - tax - other
		eos = approved * 12 if service_years >= 30 else 0
		frappe.get_doc({
			"doctype": "Pension Calculation", "employee_profile": num,
			"employee_name": prof.employee_name, "rule_set": RULE_SET,
			"calculation_date": "2024-02-15", "period_date": "2024-02-01",
			"status": "Approved" if k % 2 == 0 else "Calculated",
			"service_years": service_years, "average_36_months": approved + 100000,
			"accrual_rate": 2.5, "approved_pension": approved,
			"certificate_allowance": cert, "cost_of_living": col, "gross_pension": gross,
			"monthly_tax": tax, "other_deductions": other, "net_pension": net,
			"end_of_service_bonus": eos,
		}).insert(ignore_permissions=True)
		created += 1
	_commit()
	return created


def _seed_requests(doctype, statuses):
	"""Create draft increment/promotion requests in varied approval states. Drafts
	(docstatus 0) — demo records only; not submitted/applied."""
	if frappe.db.exists(doctype, {"employee_profile": _emp_number(2)}):
		return 0
	created = 0
	for k, status in enumerate(statuses):
		num = _emp_number(2 + k)
		if not frappe.db.exists("Government Employee Payroll Profile", num):
			continue
		prof = frappe.get_doc("Government Employee Payroll Profile", num)
		frappe.get_doc({
			"doctype": doctype, "employee_profile": num,
			"employee_name": prof.employee_name, "approval_status": status,
		}).insert(ignore_permissions=True)
		created += 1
	_commit()
	return created


def seed_demo():
	"""Idempotently seed the full demo dataset; returns a summary dict."""
	_seed_entities()
	_seed_account_mapping()
	emp = _seed_employees()
	runs = _seed_runs()
	pensions = _seed_pensions()
	increments = _seed_requests("Annual Increment Request", ["Approved", "Approved", "Draft", "HR Review"])
	promotions = _seed_requests("Promotion Request", ["Approved", "Draft", "Committee", "Approved"])
	summary = {
		"entities": len(ENTITIES),
		"employees_total": frappe.db.count("Government Employee Payroll Profile",
											{"employee_number": ["like", "DEMO-EMP-%"]}),
		"employees_created": emp,
		"runs": runs,
		"pensions_created": pensions,
		"increments_created": increments,
		"promotions_created": promotions,
	}
	print("DEMO SEED SUMMARY:", summary)
	return summary
