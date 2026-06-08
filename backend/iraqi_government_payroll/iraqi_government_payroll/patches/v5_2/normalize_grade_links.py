# Copyright (c) 2026, Iraqi Government Payroll
"""Phase 5 M4.2 — normalize grade Links across rule/request DocTypes.

Backfills the new Link -> Government Grade fields from the legacy Int grade
fields on existing records, and marks every master grade active. The Data->Link
conversions (Promotion Grade Duration from/to_grade, Employee Appointment
grade_code) need NO backfill — their stored values already equal the master
record names. Uses db.set_value so it bypasses validate()/docstatus (no
re-validation during migration). Idempotent: only fills Links that are still
empty, and only when the legacy value maps to an existing master row. Never
touches immutable Salary Slip / Payroll Calculation Snapshot copies or any
payroll amount.
"""

import frappe


def _grade_exists(code):
	return bool(code) and frappe.db.exists("Government Grade", str(code))


def _backfill_int_to_link(doctype, int_field, link_field):
	"""Set link_field = str(int_field) where the Link is empty and the Int maps to
	a master row. Int sentinels (0 / None) are skipped."""
	rows = frappe.get_all(doctype, filters={link_field: ["in", [None, ""]]},
						  fields=["name", int_field])
	filled = 0
	for r in rows:
		val = r.get(int_field)
		if val in (None, "", 0):
			continue
		code = str(val)
		if _grade_exists(code):
			frappe.db.set_value(doctype, r["name"], link_field, code, update_modified=False)
			filled += 1
	return filled


def execute():
	# 1. Every master grade active (the renamed grade_name_* labels come from the
	#    fixture re-import; the `active` column defaults to 1, set it explicitly too).
	for name in frappe.get_all("Government Grade", pluck="name"):
		if not frappe.db.get_value("Government Grade", name, "active"):
			frappe.db.set_value("Government Grade", name, "active", 1, update_modified=False)

	# 2. Backfill the new Link mirrors from the legacy Int grade fields.
	_backfill_int_to_link("Government Employee Payroll Profile",
						  "appointment_grade", "appointment_grade_ref")
	_backfill_int_to_link("Qualification Appointment Rule",
						  "starting_grade", "starting_grade_ref")
	_backfill_int_to_link("Promotion Request", "from_grade", "from_grade_ref")
	_backfill_int_to_link("Promotion Request", "to_grade", "to_grade_ref")
	_backfill_int_to_link("Annual Increment Request", "current_grade", "current_grade_ref")

	frappe.db.commit()
