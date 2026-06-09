# Copyright (c) 2026, Iraqi Government Payroll
"""Whitelisted endpoints to GENERATE and PRINT the Government Payroll Slip.

The slip is assembled AFTER payroll calculation from the immutable Payroll
Calculation Snapshot (source of truth); if a slip is still a draft and has no
snapshot yet, it falls back to the calculated Salary Slip doc (same stored
values). No payroll recalculation happens here — the engine is never touched.
"""

import frappe

from iraqi_government_payroll.services.slip.slip_builder import build_slip
from iraqi_government_payroll.services.reports.slip_pdf import build_slip_html, render_slip_pdf

_SCALAR_FIELDS = (
	"list_sequence", "payroll_date", "payment_officer", "payment_number",
	"entity_name", "department_name", "position_title", "payroll_month", "payroll_year",
	"employee_name", "employee_number", "unified_national_id", "qualification",
	"marital_status", "appointment_date", "grade", "stage",
	"promotion_year", "years_of_service", "leave_balance_annual", "leave_balance_sick",
	"base_salary", "adjustment_amount", "total_allowances", "total_rewards",
	"total_entitlement", "total_deductions", "total_misc_deductions", "net_pay",
	"amount_before_rounding", "amount_after_rounding",
)


def _position_title(profile):
	"""Arabic position title from the employee's (current) Government Position."""
	pos = profile.get("current_position") or profile.get("government_position")
	if pos and frappe.db.exists("Government Position", pos):
		return frappe.db.get_value("Government Position", pos, "position_name_ar")
	return None


def _entity_names(profile):
	"""(entity_name = root ministry, department_name = immediate unit) for a profile."""
	code = profile.get("current_entity") or profile.get("government_entity")
	if not code or not frappe.db.exists("Government Entity", code):
		return None, None
	dept = frappe.db.get_value("Government Entity", code, "entity_name_ar")
	# walk to the root (top ministry/company)
	root = code
	seen = set()
	while root and root not in seen:
		seen.add(root)
		parent = frappe.db.get_value("Government Entity", root, "parent_government_entity")
		if not parent:
			break
		root = parent
	ministry = frappe.db.get_value("Government Entity", root, "entity_name_ar") if root else dept
	return ministry, dept


def _source_view(slip):
	"""Return the snapshot-shaped source dict for a Salary Slip — preferring the
	immutable Payroll Calculation Snapshot, falling back to the slip doc itself."""
	import json

	snap_name = frappe.db.get_value(
		"Payroll Calculation Snapshot",
		{"salary_slip": slip.name, "calculation_type": "Salary Slip"}, "name") \
		or frappe.db.get_value(
		"Payroll Calculation Snapshot", {"salary_slip": slip.name}, "name")
	if snap_name:
		snap = frappe.get_doc("Payroll Calculation Snapshot", snap_name)
		try:
			output = json.loads(snap.output_snapshot or "{}")
		except (ValueError, TypeError):
			output = {}
		lines = snap.lines
		return snap.name, {
			"grade_code": snap.grade_code, "stage": snap.stage,
			"gross_amount": snap.gross_amount, "total_deductions": snap.total_deductions,
			"net_amount": snap.net_amount, "output": output,
			"lines": [_line(l) for l in lines],
		}
	# fallback: the calculated Salary Slip doc (same post-calc values)
	return None, {
		"grade_code": slip.grade_code, "stage": slip.stage,
		"gross_amount": slip.total_earnings, "total_deductions": slip.total_deductions,
		"net_amount": slip.net_salary, "output": {"basic_salary": slip.basic_salary},
		"lines": [_line(l) for l in slip.lines],
	}


def _line(l):
	return {
		"component_code": l.component_code, "component_name": l.component_name,
		"line_type": l.line_type, "amount": l.amount,
		"basis_amount": l.basis_amount, "rate": l.rate,
	}


def _list_sequence(slip):
	if not slip.payroll_run:
		return 1
	names = frappe.get_all("Salary Slip", filters={"payroll_run": slip.payroll_run},
						   order_by="employee_profile asc", pluck="name")
	return (names.index(slip.name) + 1) if slip.name in names else 1


@frappe.whitelist()
def generate_payroll_slip(salary_slip):
	"""Create/refresh the Government Payroll Slip for a Salary Slip and return its name.
	DocType create/write permission is enforced by Frappe (no ignore_permissions)."""
	slip = frappe.get_doc("Salary Slip", salary_slip)
	profile = frappe.get_doc(
		"Government Employee Payroll Profile", slip.employee_profile).as_dict()
	period = frappe.get_doc("Payroll Period", slip.payroll_period).as_dict() if slip.payroll_period else {}
	ministry, dept = _entity_names(profile)
	snap_name, source = _source_view(slip)

	data = build_slip(
		source, profile=profile, period=period,
		org={"entity_name": ministry, "department_name": dept,
			 "position_title": _position_title(profile)},
		meta={"list_sequence": _list_sequence(slip), "payroll_date": period.get("end_date")},
	)

	existing = frappe.db.get_value("Government Payroll Slip", {"salary_slip": slip.name}, "name")
	doc = frappe.get_doc("Government Payroll Slip", existing) if existing else frappe.new_doc("Government Payroll Slip")
	doc.salary_slip = slip.name
	doc.snapshot = snap_name
	doc.payroll_run = slip.payroll_run
	doc.employee_profile = slip.employee_profile
	for f in _SCALAR_FIELDS:
		doc.set(f, data.get(f))
	for table, key in (("allowance_lines", "allowance_lines"),
					   ("deduction_lines", "deduction_lines"),
					   ("misc_deduction_lines", "misc_deduction_lines")):
		doc.set(table, [])
		for row in data.get(key) or []:
			doc.append(table, row)
	doc.save()
	frappe.db.commit()
	return {"name": doc.name, "salary_slip": slip.name, "net_pay": doc.net_pay,
			"snapshot": snap_name, "source": "snapshot" if snap_name else "salary_slip"}


@frappe.whitelist()
def payroll_slip(name):
	"""Read a generated Government Payroll Slip (incl. child tables)."""
	return frappe.get_doc("Government Payroll Slip", name).as_dict()


def _logo_data_uri():
	"""Base64 data URI for the configured government/ministry logo, or None."""
	import base64
	logo = frappe.db.get_single_value("Government Payroll Settings", "government_logo")
	if not logo:
		return None
	try:
		fname = logo.split("/files/")[-1]
		fdoc = frappe.get_all("File", filters={"file_name": fname}, fields=["name"], limit=1) \
			or frappe.get_all("File", filters={"file_url": logo}, fields=["name"], limit=1)
		content = frappe.get_doc("File", fdoc[0]["name"]).get_content()
		mime = "image/png" if logo.lower().endswith("png") else "image/jpeg"
		return f"data:{mime};base64," + base64.b64encode(content).decode("ascii")
	except Exception:
		return None


def _render_pdf_response(slip_doc):
	data = slip_doc.as_dict()
	data["logo_uri"] = _logo_data_uri()
	html = build_slip_html(data)
	frappe.response["filename"] = f"payroll-slip-{slip_doc.employee_number or slip_doc.name}.pdf"
	frappe.response["filecontent"] = render_slip_pdf(html)
	frappe.response["type"] = "binary"


@frappe.whitelist()
def render_payroll_slip_pdf(salary_slip=None, name=None):
	"""Stream the slip PDF. Pass an existing slip `name`, or a `salary_slip` to
	generate-then-print in one call."""
	if not name:
		name = generate_payroll_slip(salary_slip)["name"]
	_render_pdf_response(frappe.get_doc("Government Payroll Slip", name))


# field -> where its value comes from (for the data-completeness audit).
_FIELD_SOURCES = {
	"entity_name": "Government Entity (root ministry)",
	"department_name": "Government Entity (employee unit)",
	"position_title": "Government Position.position_name_ar",
	"employee_name": "Employee Profile", "employee_number": "Employee Profile",
	"unified_national_id": "Employee Profile.national_id",
	"qualification": "Employee Profile", "marital_status": "Employee Profile",
	"appointment_date": "Employee Profile",
	"grade": "Payroll Calculation Snapshot", "stage": "Payroll Calculation Snapshot",
	"base_salary": "Snapshot output (basic_salary)",
	"total_allowances": "Snapshot earning lines",
	"total_deductions": "Snapshot (total_deductions)",
	"total_entitlement": "Derived (base + allowances)",
	"net_pay": "Snapshot (net_amount)",
	"amount_before_rounding": "Derived (= net)",
	"amount_after_rounding": "Derived (net rounded to 250 IQD, print-only)",
	"years_of_service": "Derived (appointment/service date -> payroll date)",
	"promotion_year": "Derived (last_promotion_date / current_grade_date)",
	"payroll_month": "Payroll Period", "payroll_year": "Payroll Period",
	"payroll_date": "Payroll Period (end_date)",
	"list_sequence": "Derived (employee order within the run)",
	"adjustment_amount": "Employee Profile.protected_salary_difference",
	"total_misc_deductions": "Manual misc deductions on the slip",
	"payment_officer": "Manual / not captured",
	"payment_number": "Manual / not captured",
	"leave_balance_annual": "Leave module — not implemented",
	"leave_balance_sick": "Leave module — not implemented",
	"total_rewards": "Rewards/bonus input — not captured",
}
_NEEDS = {
	"payment_officer": "Add a payment-officer (أمين الصرف) field to the Payroll Run or Settings.",
	"payment_number": "Add a disbursement-order number (رقم أمر الصرف) to the Payroll Run.",
	"leave_balance_annual": "Requires a leave/attendance module storing annual-leave balances.",
	"leave_balance_sick": "Requires a leave/attendance module storing sick-leave balances.",
	"total_rewards": "Requires a rewards/bonus input feeding the slip.",
	"position_title": "Set the employee's Government Position (current_position).",
	"qualification": "Set the employee's qualification on the profile.",
	"marital_status": "Set marital status on the profile.",
	"appointment_date": "Set the appointment date on the profile.",
	"unified_national_id": "Set the national ID on the profile.",
	"promotion_year": "Set last_promotion_date or current_grade_date on the profile.",
}


@frappe.whitelist()
def slip_field_audit(name=None, salary_slip=None):
	"""Audit every slip field: which are populated, which are empty/default, the
	source of each, and what data is needed to fill the empty ones."""
	if not name:
		name = generate_payroll_slip(salary_slip)["name"]
	doc = frappe.get_doc("Government Payroll Slip", name)
	populated, empty = [], []
	for f, src in _FIELD_SOURCES.items():
		v = doc.get(f)
		row = {"field": f, "value": v, "source": src}
		if v in (None, "", 0):
			row["reason"] = ("No source value for this employee/run."
							 if f not in _NEEDS else "Default/empty.")
			row["needs"] = _NEEDS.get(f, "Provide the value in the source record above.")
			empty.append(row)
		else:
			populated.append(row)
	# completeness warnings (critical fields that should not be blank on a real slip)
	critical = ("employee_name", "employee_number", "unified_national_id", "grade",
				"stage", "base_salary", "net_pay", "entity_name")
	warnings = [f"حقل ناقص: {f}" for f in critical if doc.get(f) in (None, "", 0)]
	return {"slip": name, "populated": populated, "empty": empty, "warnings": warnings,
			"counts": {"populated": len(populated), "empty": len(empty),
					   "allowance_lines": len(doc.allowance_lines),
					   "deduction_lines": len(doc.deduction_lines)}}


@frappe.whitelist()
def font_debug():
	"""Font diagnostic: bundled paths, install status, and fontconfig Cairo matches."""
	from iraqi_government_payroll.services.reports import slip_pdf
	slip_pdf._ensure_fonts_installed()
	return slip_pdf.font_debug()


@frappe.whitelist()
def generate_latest_slip(employee):
	"""Generate (write) the payroll slip for an employee's most recent Salary Slip
	and return its name. Use POST; the PDF is then fetched read-only by name."""
	slip = frappe.db.get_value(
		"Salary Slip", {"employee_profile": employee}, "name", order_by="modified desc")
	if not slip:
		frappe.throw("لا توجد قسيمة راتب محتسبة لهذا الموظف.")
	return generate_payroll_slip(slip)


@frappe.whitelist()
def latest_slip_pdf(employee):
	"""One-click print: find the employee's most recent Salary Slip, generate the
	payroll slip and stream its PDF."""
	slip = frappe.db.get_value(
		"Salary Slip", {"employee_profile": employee}, "name",
		order_by="modified desc")
	if not slip:
		frappe.throw("لا توجد قسيمة راتب محتسبة لهذا الموظف.")
	name = generate_payroll_slip(slip)["name"]
	_render_pdf_response(frappe.get_doc("Government Payroll Slip", name))
