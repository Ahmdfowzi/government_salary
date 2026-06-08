# Copyright (c) 2026, Iraqi Government Payroll
"""Phase 5 M4.1 — backfill the new Government Grade Link on existing data.

Ensures the Government Grade master rows exist, then sets the `grade` Link on
employee profiles (from grade_code / current_grade) and the `grade_ref` Link on
salary-scale-detail rows (from grade_code). Uses db.set_value so it bypasses the
profile validate()/sync (no re-validation during migration). Idempotent: only
fills rows whose Link is still empty. Never touches immutable snapshots or payroll
results.
"""

import frappe

GRADES = [
	("SPECIAL_A", "Senior", 1), ("SPECIAL_B", "Senior", 2), ("SPECIAL_C", "Senior", 3),
	("1", "Regular", 4), ("2", "Regular", 5), ("3", "Regular", 6), ("4", "Regular", 7),
	("5", "Regular", 8), ("6", "Regular", 9), ("7", "Regular", 10), ("8", "Regular", 11),
	("9", "Regular", 12), ("10", "Regular", 13),
]


def execute():
	# 1. Government Grade master (in case fixtures have not been imported yet).
	for code, gtype, order in GRADES:
		if not frappe.db.exists("Government Grade", code):
			frappe.get_doc({
				"doctype": "Government Grade", "grade_code": code,
				"grade_type": gtype, "sort_order": order,
			}).insert(ignore_permissions=True)

	# 2. Profiles: grade = grade_code (or the legacy Int) where still empty.
	for p in frappe.get_all("Government Employee Payroll Profile",
							filters={"grade": ["in", [None, ""]]},
							fields=["name", "grade_code", "current_grade"]):
		code = p.get("grade_code") or (str(p.get("current_grade")) if p.get("current_grade") else None)
		if code and frappe.db.exists("Government Grade", code):
			frappe.db.set_value("Government Employee Payroll Profile", p["name"], "grade", code,
								update_modified=False)

	# 3. Salary scale details: grade_ref = grade_code where still empty.
	for d in frappe.get_all("Government Salary Scale Detail",
							filters={"grade_ref": ["in", [None, ""]]},
							fields=["name", "grade_code"]):
		if d.get("grade_code") and frappe.db.exists("Government Grade", d["grade_code"]):
			frappe.db.set_value("Government Salary Scale Detail", d["name"], "grade_ref",
								d["grade_code"], update_modified=False)

	frappe.db.commit()
