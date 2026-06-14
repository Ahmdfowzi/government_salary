# Copyright (c) 2026, Iraqi Government Payroll
"""Frappe-backed data loader for the active-salary engine.

This is the production wiring: it reads the rule set / scale / allowance data
from the Frappe DB and builds a DataContext, then delegates to the pure engine.
``frappe`` is imported lazily so the pure engine modules stay testable without a
bench.
"""

from .engine import DataContext, EmployeeInput, calculate_active_salary
from .scale_resolver import resolve_grade_code, get_active_scale
from .net_salary import compute_net_salary

_FAMILY_SUMMARY_FIELDS = (
	"spouse_count", "children_count", "eligible_children_count", "dependents_count",
	"eligible_dependents_count", "disabled_dependents_count",
	"employed_dependents_count", "student_dependents_count",
)


def _family_summary(profile):
	"""Snapshot of the profile's computed dependent counts (Frappe doc or dict).
	Recorded into the snapshot input so historical payroll is immutable."""
	get = profile.get if hasattr(profile, "get") else (lambda k: getattr(profile, k, None))
	return {f: (get(f) or 0) for f in _FAMILY_SUMMARY_FIELDS}


def load_context() -> "DataContext":
	import frappe

	rule_sets = frappe.get_all(
		"Government Rule Set",
		fields=["name", "rule_set_code", "status", "effective_from", "effective_to"],
	)

	scales = []
	for s in frappe.get_all("Government Salary Scale", fields=["name", "rule_set", "is_active"]):
		doc = frappe.get_doc("Government Salary Scale", s["name"])
		s["details"] = [
			{"grade_code": d.grade_code, "grade": d.grade, "stage": d.stage,
			 "basic_salary": d.basic_salary}
			for d in doc.details
		]
		scales.append(s)

	allowance_rules = frappe.get_all(
		"Allowance Rule",
		fields=["name", "component_code", "component_name", "rule_set", "allowance_type",
				"context", "match_key", "match_value", "calculation_type", "basis",
				"percentage", "fixed_amount", "capped_under_200", "confirmed", "is_active"],
	)
	income_tax_brackets = frappe.get_all(
		"Income Tax Bracket",
		fields=["name", "rule_set", "seq", "from_amount", "to_amount", "rate"],
	)
	tax_allowance_rules = frappe.get_all(
		"Tax Allowance Rule",
		fields=["name", "rule_set", "taxpayer_status", "basis", "annual_amount",
				"max_annual_cap", "confirmed"],
	)
	return DataContext(
		rule_sets=rule_sets, scales=scales, allowance_rules=allowance_rules,
		income_tax_brackets=income_tax_brackets, tax_allowance_rules=tax_allowance_rules,
	)


def calculate_for_profile(profile_name, period_date):
	"""Convenience entry point: compute active salary for an employee profile.

	Uses profile.grade_code as the canonical key (supports senior grades), and
	falls back to str(current_grade) only when grade_code is empty.
	"""
	import frappe

	p = frappe.get_doc("Government Employee Payroll Profile", profile_name)
	emp = EmployeeInput(
		grade_code=resolve_grade_code(p.get("grade") or p.get("grade_code"), p.get("current_grade")),
		stage=p.current_stage,
		period_date=period_date,
		qualification=p.qualification,
		position_allowance_category=None,
		risk_applicable=bool(p.risk_allowance_applicable),
		risk_category=p.risk_category,
		spouse_eligible=(p.marital_status == "Married"),
		children_count=p.eligible_children_count or 0,
		family_summary=_family_summary(p),
	)
	return calculate_active_salary(load_context(), emp)


def _employee_input_from_profile(profile, period_date):
	return EmployeeInput(
		grade_code=resolve_grade_code(profile.get("grade") or profile.get("grade_code"),
									  profile.get("current_grade")),
		stage=profile.get("current_stage"),
		period_date=str(period_date),
		qualification=profile.get("qualification"),
		position_allowance_category=None,
		risk_applicable=bool(profile.get("risk_allowance_applicable")),
		risk_category=profile.get("risk_category"),
		spouse_eligible=(profile.get("marital_status") == "Married"),
		children_count=profile.get("eligible_children_count") or 0,
		family_summary=_family_summary(profile),
	)


def compute_salary_slip(slip):
	"""Compute and populate a Salary Slip document from the engines. Returns the result."""
	import frappe

	profile = frappe.get_doc("Government Employee Payroll Profile", slip.employee_profile)
	period_date = None
	if slip.payroll_period:
		period_date = frappe.db.get_value("Payroll Period", slip.payroll_period, "start_date")
	period_date = period_date or frappe.utils.today()

	emp = _employee_input_from_profile(profile, period_date)
	res = compute_net_salary(load_context(), emp, other_deductions=0)

	slip.rule_set = res.rule_set
	slip.grade_code = res.grade_code
	slip.grade = int(res.grade_code) if str(res.grade_code).isdigit() else 0
	slip.stage = res.stage
	slip.basic_salary = res.basic_salary
	slip.total_capped_allowances = res.capped_allowance_total
	slip.total_non_capped_allowances = res.non_capped_allowance_total
	slip.total_earnings = res.gross_salary
	slip.total_deductions = res.total_deductions
	slip.net_salary = res.net_salary

	lines = []
	for l in res.allowance_lines:
		lines.append({"component_code": l.component_code, "component_name": l.component_name,
					  "line_type": l.line_type, "amount": l.amount, "basis_amount": l.basis_amount,
					  "rate": l.rate, "cap_applied": 1 if l.cap_applied else 0,
					  "source_rule": l.source_rule, "reason_text": l.reason_text})
	if res.pension_deduction:
		lines.append({"component_code": "DED_PENSION", "component_name": "Pension Contribution",
					  "line_type": "Deduction", "amount": res.pension_deduction})
	if res.tax:
		lines.append({"component_code": "INCOME_TAX", "component_name": "Income Tax",
					  "line_type": "Deduction", "amount": res.tax})
	slip.set("lines", lines)
	return res


def write_salary_slip_snapshot(slip):
	"""Compute the slip again and persist an immutable Salary Slip snapshot (once)."""
	import frappe
	from ..audit.audit_service import build_net_salary_snapshot_payload, write_payload

	# Idempotency guard: one Salary Slip snapshot per slip.
	if frappe.db.exists("Payroll Calculation Snapshot",
						{"salary_slip": slip.name, "calculation_type": "Salary Slip"}):
		return None

	res = compute_salary_slip(slip)
	payload = build_net_salary_snapshot_payload(res, employee_profile=slip.employee_profile,
											   salary_slip=slip.name)
	return write_payload(payload)


def apply_increment(request):
	"""Apply an Annual Increment Request to its employee profile + write snapshot."""
	import frappe
	from ..increment.increment_service import compute_increment
	from ..audit.audit_service import build_increment_snapshot_payload, write_payload

	# Idempotency guard: do not apply the same request twice.
	if frappe.db.exists("Payroll Calculation Snapshot",
						{"calculation_type": "Annual Increment", "source_request": request.name}):
		frappe.throw("This increment request has already been applied.")

	profile = frappe.get_doc("Government Employee Payroll Profile", request.employee_profile)
	rule = (frappe.get_doc("Annual Increment Rule", profile.rule_set).as_dict()
			if frappe.db.exists("Annual Increment Rule", profile.rule_set) else {})
	effective_date = request.get("due_date") or frappe.utils.today()
	gc = resolve_grade_code(profile.get("grade") or profile.get("grade_code"), profile.get("current_grade"))

	res = compute_increment(
		{"grade_code": gc, "current_stage": profile.current_stage,
		 "current_stage_date": str(profile.current_stage_date) if profile.current_stage_date else None},
		rule, str(effective_date), rule_set=profile.rule_set)

	if not res.applied:
		frappe.throw("; ".join(res.warnings) or "Increment not applicable.")

	for k, v in res.profile_mutation.items():
		profile.set(k, v)
	profile.save()

	# M4.2: record the (unchanged) grade as a Link too; increments never change grade.
	request.current_grade_ref = str(gc)
	request.current_stage = res.old_state["current_stage"]
	request.new_stage = res.new_state["current_stage"]
	write_payload(build_increment_snapshot_payload(res, employee_profile=profile.name,
												  source_request=request.name))
	return res


def apply_promotion(request):
	"""Apply a Promotion Request to its employee profile + write snapshot."""
	import frappe
	from ..promotion.promotion_service import compute_promotion
	from ..audit.audit_service import build_promotion_snapshot_payload, write_payload

	# Idempotency guard: do not apply the same request twice.
	if frappe.db.exists("Payroll Calculation Snapshot",
						{"calculation_type": "Promotion", "source_request": request.name}):
		frappe.throw("This promotion request has already been applied.")

	profile = frappe.get_doc("Government Employee Payroll Profile", request.employee_profile)
	promotion_rule = frappe.get_doc("Promotion Rule", profile.rule_set).as_dict()
	effective_date = request.get("due_date") or frappe.utils.today()
	gc = resolve_grade_code(profile.get("grade") or profile.get("grade_code"), profile.get("current_grade"))

	scale = get_active_scale(load_context().scales, profile.rule_set)
	res = compute_promotion(
		{"grade_code": gc, "current_stage": profile.current_stage,
		 "current_grade_date": str(profile.current_grade_date) if profile.current_grade_date else None},
		promotion_rule, scale.get("details", []), str(effective_date), rule_set=profile.rule_set)

	if not res.applied:
		frappe.throw("; ".join(res.warnings) or "Promotion not applicable.")

	for k, v in res.profile_mutation.items():
		profile.set(k, v)
	# Promotion changes the grade: keep the new `grade` Link in step with the
	# updated grade_code mirror (M4.1). Does NOT depend on Government Position.
	profile.grade = profile.grade_code
	profile.save()

	# M4.2: authoritative grade Links (record name == grade code) + legacy Int mirrors.
	request.from_grade_ref = str(res.old_state["grade_code"])
	request.to_grade_ref = str(res.to_grade)
	request.from_grade = res.old_state["grade_code"] if str(res.old_state["grade_code"]).isdigit() else 0
	request.to_grade = int(res.to_grade) if str(res.to_grade).isdigit() else 0
	request.proposed_stage = res.new_stage
	request.old_salary = res.old_salary
	request.new_salary = res.new_salary
	write_payload(build_promotion_snapshot_payload(res, employee_profile=profile.name,
												  source_request=request.name))
	return res


class FrappeSlipStore:
	"""Slip store backed by Frappe — upserts DRAFT Salary Slips idempotently.

	The Salary Slip recomputes its own fields on save (M5 controller); this store
	only ensures one draft slip per (period, employee) and never submits.
	"""

	def upsert(self, period, run, employee, rule_set, result):
		import frappe

		existing = frappe.db.get_value(
			"Salary Slip",
			{"employee_profile": employee, "payroll_period": period, "docstatus": 0},
			"name")
		if existing:
			doc = frappe.get_doc("Salary Slip", existing)
			doc.payroll_run = run
			doc.save()                         # validate() recomputes fields
			return doc.name, False
		doc = frappe.new_doc("Salary Slip")
		doc.employee_profile = employee
		doc.payroll_period = period
		doc.payroll_run = run
		doc.insert()                           # validate() computes fields; not submitted
		return doc.name, True


def _has_active_scale(rule_set):
	import frappe
	return bool(frappe.db.exists("Government Salary Scale", {"rule_set": rule_set, "is_active": 1})
				or frappe.db.exists("Government Salary Scale", {"rule_set": rule_set}))


def _eligible_filters(run):
	filters = {"employment_status": "Active"}
	if run.scope == "Employee" and run.scope_reference:
		filters["name"] = run.scope_reference
	elif run.scope == "Government Entity" and run.scope_reference:
		filters["government_entity"] = run.scope_reference
	if run.rule_set:
		filters["rule_set"] = run.rule_set
	return filters


def ensure_calculable(run):
	"""Block a payroll run before it starts if the financial CONFIG needed to
	calculate is missing (rule set / active salary scale), with one clear message
	instead of per-employee failures. Item 11 guard.

	An empty employee scope is NOT an error — it produces an empty run (0 slips);
	per-employee grade/stage validity is enforced at profile save and isolated per
	row during the batch."""
	import frappe

	if run.rule_set and not frappe.db.exists("Government Rule Set", run.rule_set):
		frappe.throw(f"تعذّر الاحتساب: مجموعة القواعد «{run.rule_set}» غير موجودة. "
					 f"(Cannot calculate: rule set '{run.rule_set}' does not exist.)")
	if run.rule_set:
		if not _has_active_scale(run.rule_set):
			frappe.throw(f"تعذّر الاحتساب: لا يوجد سلم رواتب فعّال لمجموعة القواعد «{run.rule_set}». "
						 f"(Cannot calculate: rule set '{run.rule_set}' has no active salary scale.)")
	elif not (frappe.db.exists("Government Salary Scale", {"is_active": 1})
			  or frappe.db.exists("Government Salary Scale", {})):
		frappe.throw("تعذّر الاحتساب: لا يوجد سلم رواتب مُعدّ. "
					 "(Cannot calculate: no salary scale is configured.)")


def run_payroll(run):
	"""Execute a Payroll Run: build draft slips for eligible profiles + tally results."""
	import frappe
	from .payroll_run import run_payroll_batch, STATUS_PROCESSING

	ensure_calculable(run)                  # fail fast with a clear message (item 11)
	run.run_status = STATUS_PROCESSING
	run.started_at = frappe.utils.now()
	run.save()

	rule_set = run.rule_set
	# Lifecycle integration: only Active employees participate in payroll
	# (retired / terminated / on-leave-without-salary are excluded).
	filters = _eligible_filters(run)

	profiles = frappe.get_all(
		"Government Employee Payroll Profile", filters=filters,
		fields=["name", "grade", "grade_code", "current_grade", "current_stage",
				"qualification", "risk_allowance_applicable", "risk_category",
				"marital_status", "rule_set", *_FAMILY_SUMMARY_FIELDS])

	period_date = frappe.db.get_value("Payroll Period", run.payroll_period, "start_date") \
		or frappe.utils.today()

	res = run_payroll_batch(run.payroll_period, run.name, rule_set, profiles,
							load_context(), FrappeSlipStore(), str(period_date))

	run.run_status = res.status
	run.total_employees = res.total_employees
	run.processed_count = res.processed_count
	run.success_count = res.success_count
	run.warning_count = res.warning_count
	run.error_count = res.error_count
	run.finished_at = frappe.utils.now()
	run.error_log = "\n".join(res.error_log)
	run.run_date = frappe.utils.now()
	run.save()
	return res


def load_pension_rule_data(rule_set_code):
	"""Load (pension_rule, certificate_rules, tax_brackets) for a rule set from Frappe."""
	import frappe

	pension_rule = frappe.get_doc("Pension Rule", rule_set_code).as_dict()
	certificate_rules = frappe.get_all(
		"Allowance Rule",
		filters={"rule_set": rule_set_code, "match_key": "Pension Certificate"},
		fields=["component_code", "match_key", "match_value", "percentage", "confirmed"],
	)
	tax_brackets = frappe.get_all(
		"Income Tax Bracket",
		filters={"rule_set": rule_set_code},
		fields=["seq", "from_amount", "to_amount", "rate"],
	)
	return pension_rule, certificate_rules, tax_brackets

