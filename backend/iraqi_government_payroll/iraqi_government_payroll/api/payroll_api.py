# Copyright (c) 2026, Iraqi Government Payroll
"""Whitelisted REST endpoints consumed by the Next.js frontend.

All calculations happen on the backend; the frontend only reads/writes data and
triggers these endpoints. Phase 1 declares the surface; logic lands in Phase 2.
"""

import json

import frappe

from iraqi_government_payroll.services.payroll_engine import governance


@frappe.whitelist()
def calculate_active_salary(profile, period_date):
	"""Trigger the payroll engine for one employee profile."""
	raise NotImplementedError("Phase 2: wire to services.payroll_engine.engine")


@frappe.whitelist()
def evaluate_increment(profile):
	"""Preview the annual increment for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.increment.increment_service")


@frappe.whitelist()
def evaluate_promotion(profile):
	"""Preview a promotion for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.promotion.promotion_service")


@frappe.whitelist()
def compute_pension(profile, calculation_date):
	"""Compute the pension for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.pension.pension_service")


# --- Payroll Run governance (Phase 3 M6) --- #
# Thin REST surface over the Payroll Run controller's governance transitions. Each
# action maps to a controller method that ALREADY enforces role (M4) and writes an
# immutable audit event (M5); these endpoints only route — no authorization, state
# machine or audit logic is duplicated here.

_ACTION_METHODS = {
	"calculate": "calculate_run",
	"submit_for_review": "submit_for_review",
	"approve": "approve_run",
	"submit": "submit_run",
	"cancel": "cancel_run",
	"lock": "lock_run",
	"unlock": "unlock_run",
}

_AUDIT_FIELDS = (
	"calculated_by", "calculated_on", "reviewed_by", "reviewed_on",
	"approved_by", "approved_on", "submitted_by", "submitted_on",
	"locked_by", "locked_on", "unlocked_by", "unlocked_on",
)


@frappe.whitelist()
def run_governance_action(run, action):
	"""Perform one governance transition on a Payroll Run.

	`action` is one of GOVERNANCE_ACTIONS. The matching controller method enforces
	role + writes the audit event + transitions state; this only dispatches.
	Returns the new workflow_state and the actions now available to the caller.
	"""
	if action not in _ACTION_METHODS:
		frappe.throw(f"Unknown payroll run action: {action}")
	doc = frappe.get_doc("Payroll Run", run)
	getattr(doc, _ACTION_METHODS[action])()
	return {
		"name": doc.name,
		"workflow_state": doc.workflow_state,
		"allowed_actions": governance.available_actions(
			doc.workflow_state, frappe.get_roles(frappe.session.user)),
	}


@frappe.whitelist()
def current_user():
	"""The logged-in user + their roles — for role-aware UI only (Phase 5 M2).

	Read-only; the backend remains the source of truth for every restriction.
	"""
	user = frappe.session.user
	return {"user": user, "roles": frappe.get_roles(user)}


@frappe.whitelist()
def get_run_governance(run):
	"""Read-only governance view of a Payroll Run: current state, the actions the
	caller may take now, the per-transition audit fields, and the immutable event
	trail (oldest first)."""
	doc = frappe.get_doc("Payroll Run", run)
	roles = frappe.get_roles(frappe.session.user)
	events = frappe.get_all(
		"Payroll Run Governance Event",
		filters={"payroll_run": run},
		fields=["action", "from_state", "to_state", "actor", "event_timestamp"],
		order_by="creation asc")
	return {
		"name": doc.name,
		"workflow_state": doc.workflow_state,
		"run_status": doc.get("run_status"),
		"error_count": doc.get("error_count"),
		"allowed_actions": governance.available_actions(doc.workflow_state, roles),
		"audit": {f: doc.get(f) for f in _AUDIT_FIELDS},
		"events": events,
	}


_SCOPES = ("All", "Government Entity", "Employee")
_SCOPE_REF_DOCTYPE = {
	"Employee": "Government Employee Payroll Profile",
	"Government Entity": "Government Entity",
}


@frappe.whitelist()
def create_payroll_run(period, rule_set=None, scope="All", scope_reference=None):
	"""Create a new Payroll Run (starts in Draft) after validating its inputs.

	Validation only — no governance/engine logic. Create permission is enforced by
	the Payroll Run DocType perms. Prevents a duplicate run for the same
	period + rule_set + scope + scope_reference while an existing one is not
	Cancelled. Returns the new run's name, workflow_state and available actions.
	"""
	scope = scope or "All"
	rule_set = (rule_set or "").strip() or None
	scope_reference = (scope_reference or "").strip() or None

	if scope not in _SCOPES:
		frappe.throw(f"Invalid scope '{scope}'. Expected one of: {', '.join(_SCOPES)}.")
	if not period or not frappe.db.exists("Payroll Period", period):
		frappe.throw(f"Payroll Period '{period}' does not exist.")
	if rule_set and not frappe.db.exists("Government Rule Set", rule_set):
		frappe.throw(f"Government Rule Set '{rule_set}' does not exist.")

	if scope == "All":
		scope_reference = None
	else:
		if not scope_reference:
			frappe.throw(f"A scope reference is required when scope is '{scope}'.")
		ref_doctype = _SCOPE_REF_DOCTYPE[scope]
		if not frappe.db.exists(ref_doctype, scope_reference):
			frappe.throw(f"{ref_doctype} '{scope_reference}' does not exist.")

	# Duplicate guard: no second active (non-Cancelled) run for the same target.
	for c in frappe.get_all(
			"Payroll Run",
			filters={"payroll_period": period, "scope": scope,
					 "workflow_state": ["!=", governance.CANCELLED]},
			fields=["name", "rule_set", "scope_reference"]):
		if (c.get("rule_set") or None) == rule_set \
				and (c.get("scope_reference") or None) == scope_reference:
			frappe.throw(
				f"A payroll run already exists for this period / rule set / scope: {c['name']}.")

	doc = frappe.get_doc({
		"doctype": "Payroll Run",
		"payroll_period": period,
		"rule_set": rule_set,
		"scope": scope,
		"scope_reference": scope_reference,
	}).insert()
	return {
		"name": doc.name,
		"workflow_state": doc.workflow_state,
		"allowed_actions": governance.available_actions(
			doc.workflow_state, frappe.get_roles(frappe.session.user)),
	}


# ---------------------------------------------------------------------------
# Phase 5 M5 — Employee Payroll Profile create/edit from the frontend.
#
# The frontend never computes salary; these endpoints read master data, preview
# the (grade, stage) basic salary via the SAME engine resolver the payroll uses,
# and create/update profiles. Create/write permission is enforced by Frappe (the
# DocType perms), and the profile controller validates grade+stage placement
# against the active scale. The deprecated grade mirrors (grade_code,
# current_grade, appointment_grade) are NEVER accepted from the client — the
# controller keeps them in sync from the Grade Link.
# ---------------------------------------------------------------------------

# Fields the client is allowed to set on a profile. Deliberately excludes the
# hidden/deprecated grade mirrors and engine-managed fields (basic_salary, dates).
_PROFILE_WRITABLE = (
	"employee_number", "employee_name", "rule_set",
	"government_entity", "current_entity",
	"government_position", "current_position",
	"grade", "current_stage", "qualification", "specialization",
	"employment_type", "appointment_date", "appointment_grade_ref", "appointment_stage",
	"bank_account", "bank_name", "iban", "national_id",
	"status", "marital_status", "geographic_area",
	"risk_allowance_applicable", "risk_category",
)


@frappe.whitelist()
def list_grades():
	"""Active Government Grade master rows for the grade picker (most senior first)."""
	return frappe.get_all(
		"Government Grade", filters={"active": 1},
		fields=["name as grade_code", "grade_name_ar", "grade_name_en",
				"grade_type", "sort_order"],
		order_by="sort_order asc")


def _active_scale_details(rule_set):
	"""Return (scale_name, details) for the active scale of a rule set, or (None, [])."""
	scale = frappe.db.get_value(
		"Government Salary Scale", {"rule_set": rule_set, "is_active": 1}, "name"
	) or frappe.db.get_value("Government Salary Scale", {"rule_set": rule_set}, "name")
	if not scale:
		return None, []
	return scale, frappe.get_all(
		"Government Salary Scale Detail", filters={"parent": scale},
		fields=["grade_code", "stage", "basic_salary"])


def _scale_check(rule_set, grade, stage):
	"""Validate a (grade, stage) placement in rule_set's active scale.
	Returns {valid, basic_salary, message} with an Arabic message. Pure read —
	reuses the engine resolver, never writes or computes new amounts."""
	from iraqi_government_payroll.services.payroll_engine.scale_resolver import (
		scale_has_grade_stage, get_basic_salary)

	if not (rule_set and grade and stage not in (None, "")):
		return {"valid": False, "basic_salary": None,
				"message": "اختر مجموعة القواعد والدرجة والمرحلة."}
	try:
		stage_i = int(stage)
	except (TypeError, ValueError):
		return {"valid": False, "basic_salary": None,
				"message": "المرحلة يجب أن تكون رقماً صحيحاً."}
	if not frappe.db.exists("Government Rule Set", rule_set):
		return {"valid": False, "basic_salary": None,
				"message": f"مجموعة القواعد «{rule_set}» غير موجودة."}
	scale, details = _active_scale_details(rule_set)
	if not scale:
		return {"valid": False, "basic_salary": None,
				"message": f"لا يوجد سلم رواتب فعّال لمجموعة القواعد «{rule_set}»."}
	if not scale_has_grade_stage(details, grade, stage_i):
		return {"valid": False, "basic_salary": None,
				"message": f"الدرجة «{grade}» والمرحلة «{stage_i}» غير موجودة "
						   f"في سلم الرواتب الفعّال لمجموعة القواعد «{rule_set}»."}
	return {"valid": True, "basic_salary": get_basic_salary(details, grade, stage_i),
			"message": "تركيبة صحيحة."}


@frappe.whitelist()
def salary_preview(rule_set, grade, stage):
	"""Preview the basic salary for (grade, stage). Read-only; backs the form's
	live salary preview and validation with a clear Arabic message."""
	return _scale_check(rule_set, grade, stage)


@frappe.whitelist()
def save_employee_profile(payload, name=None):
	"""Create (name omitted) or update an Employee Payroll Profile from the frontend.

	Permissions are enforced by Frappe — NO ignore_permissions — so only roles with
	create/write on the DocType (HR Officer, Payroll Manager, Government Payroll
	Administrator, …) succeed; Auditor / Read Only User are denied. Grade+stage are
	validated against the active scale (Arabic message) before save, and again by
	the controller. Returns the saved profile summary including the previewed basic.
	"""
	data = json.loads(payload) if isinstance(payload, str) else dict(payload or {})
	clean = {k: data.get(k) for k in _PROFILE_WRITABLE if data.get(k) not in (None, "")}

	# Pre-validate placement for a clear Arabic error (defense-in-depth; the
	# controller re-validates on save).
	if clean.get("grade") and clean.get("current_stage") and clean.get("rule_set"):
		chk = _scale_check(clean["rule_set"], clean["grade"], clean["current_stage"])
		if not chk["valid"]:
			frappe.throw(chk["message"])

	if name:
		doc = frappe.get_doc("Government Employee Payroll Profile", name)
		doc.update(clean)
	else:
		clean["doctype"] = "Government Employee Payroll Profile"
		doc = frappe.get_doc(clean)
	_set_family_members(doc, data)
	doc.save() if name else doc.insert()
	frappe.db.commit()

	basic = None
	if doc.grade and doc.current_stage and doc.rule_set:
		basic = _scale_check(doc.rule_set, doc.grade, doc.current_stage).get("basic_salary")
	return {
		"name": doc.name, "employee_number": doc.employee_number,
		"employee_name": doc.employee_name, "grade": doc.grade,
		"current_stage": doc.current_stage, "basic_salary": basic,
		"family_summary": {f: doc.get(f) for f in (
			"spouse_count", "children_count", "eligible_children_count", "dependents_count",
			"eligible_dependents_count", "disabled_dependents_count",
			"employed_dependents_count", "student_dependents_count")},
	}


# Family-member fields a client may set. `age` and `eligible_for_family_allowance`
# are computed by the controller and are NEVER accepted from the client.
_FAMILY_WRITABLE = (
	"full_name", "relation", "gender", "date_of_birth", "marital_status",
	"is_alive", "financially_dependent", "legal_guardianship",
	"is_employed", "employment_type", "employer_name", "monthly_income",
	"is_student", "education_level", "has_disability", "disability_type",
	"allowance_start_date", "allowance_end_date", "notes",
)


def _set_family_members(doc, data):
	"""Replace the family_members child table from the payload (whitelisted fields
	only). Omitted -> table left untouched. The controller recomputes the summary."""
	if "family_members" not in data:
		return
	doc.set("family_members", [])
	for m in data.get("family_members") or []:
		row = {k: m.get(k) for k in _FAMILY_WRITABLE if m.get(k) not in (None, "")}
		if row.get("full_name"):
			doc.append("family_members", row)


# ---------------------------------------------------------------------------
# Phase 5 M8 — create the transaction requests from the frontend. These are
# data-entry CREATE endpoints; permission is enforced by Frappe (no
# ignore_permissions). They DO NOT change any calculation logic:
#   * increment / promotion requests are created as DRAFTS — the computed grade/
#     stage/salary are filled by the engine on the request's on_submit (apply_*).
#   * the pension calculation runs the EXISTING pension service and stores its
#     result; it adds no new math.
# ---------------------------------------------------------------------------


def _require_profile(employee_profile):
	if not (employee_profile and frappe.db.exists(
			"Government Employee Payroll Profile", employee_profile)):
		frappe.throw("اختر موظفاً صحيحاً. (Select a valid employee profile.)")


@frappe.whitelist()
def create_increment_request(employee_profile, due_date=None, remarks=None):
	"""Create a DRAFT Annual Increment Request. The stage/salary are computed by the
	increment engine when the request is approved/applied — never here."""
	_require_profile(employee_profile)
	doc = frappe.get_doc({
		"doctype": "Annual Increment Request", "employee_profile": employee_profile,
		"approval_status": "Draft", "due_date": due_date or None, "remarks": remarks or None,
	}).insert()
	frappe.db.commit()
	return {"name": doc.name, "employee_profile": doc.employee_profile,
			"approval_status": doc.approval_status, "due_date": str(doc.due_date or "")}


@frappe.whitelist()
def create_promotion_request(employee_profile, vacancy_available=0,
							 direct_manager_recommendation=0, committee_decision=None,
							 remarks=None):
	"""Create a DRAFT Promotion Request. The target grade/stage/salary are computed
	by the promotion engine when the request is approved/applied — never here."""
	_require_profile(employee_profile)
	doc = frappe.get_doc({
		"doctype": "Promotion Request", "employee_profile": employee_profile,
		"approval_status": "Draft",
		"vacancy_available": 1 if int(vacancy_available or 0) else 0,
		"direct_manager_recommendation": 1 if int(direct_manager_recommendation or 0) else 0,
		"committee_decision": committee_decision or None, "remarks": remarks or None,
	}).insert()
	frappe.db.commit()
	return {"name": doc.name, "employee_profile": doc.employee_profile,
			"approval_status": doc.approval_status}


@frappe.whitelist()
def create_pension_calculation(employee_profile, service_years, average_36_months,
							   last_functional_salary, last_full_salary=0,
							   extra_months=0, other_deductions=0,
							   calculation_date=None, remarks=None):
	"""Compute a retirement pension via the EXISTING pension service and store the
	result as a Pension Calculation record. No new math is added here."""
	from iraqi_government_payroll.services.pension.pension_service import (
		compute_retirement_pension, RetirementPensionInput)
	from iraqi_government_payroll.services.payroll_engine.repository import load_pension_rule_data

	_require_profile(employee_profile)
	prof = frappe.get_doc("Government Employee Payroll Profile", employee_profile)
	if not prof.rule_set:
		frappe.throw("لا توجد مجموعة قواعد للموظف. (Employee has no rule set.)")
	try:
		pension_rule, cert_rules, brackets = load_pension_rule_data(prof.rule_set)
	except Exception:
		frappe.throw(f"لا توجد قاعدة تقاعد لمجموعة القواعد «{prof.rule_set}». "
					 f"(No Pension Rule for rule set '{prof.rule_set}'.)")

	pin = RetirementPensionInput(
		avg36=float(average_36_months or 0), service_years=int(service_years or 0),
		extra_months=int(extra_months or 0),
		last_functional_salary=float(last_functional_salary or 0),
		last_full_salary=float(last_full_salary or 0),
		qualification=prof.qualification, other_deductions=float(other_deductions or 0),
		rule_set=prof.rule_set,
		cost_of_living_method=pension_rule.get("cost_of_living_method"),
		cost_of_living_value=pension_rule.get("cost_of_living_value"))
	res = compute_retirement_pension(pin, pension_rule, cert_rules, brackets)

	doc = frappe.get_doc({
		"doctype": "Pension Calculation", "employee_profile": employee_profile,
		"employee_name": prof.employee_name, "rule_set": prof.rule_set,
		"calculation_date": calculation_date or frappe.utils.today(), "status": "Calculated",
		"service_years": int(service_years or 0), "extra_months": int(extra_months or 0),
		"average_36_months": float(average_36_months or 0),
		"last_functional_salary": float(last_functional_salary or 0),
		"last_full_salary": float(last_full_salary or 0),
		"other_deductions": float(other_deductions or 0), "remarks": remarks or None,
		"accrual_rate": pension_rule.get("accrual_rate"),
		"initial_pension": res.initial_pension, "approved_pension": res.approved_pension,
		"certificate_allowance": res.certificate_allowance, "cost_of_living": res.cost_of_living,
		"gross_pension": res.gross_pension, "taxable_income": res.taxable_income,
		"legal_allowances": res.legal_allowances, "annual_tax": res.annual_tax,
		"monthly_tax": res.monthly_tax, "net_pension": res.net_pension,
		"end_of_service_bonus": res.end_of_service_bonus,
	}).insert()
	frappe.db.commit()
	return {"name": doc.name, "employee_name": doc.employee_name,
			"approved_pension": res.approved_pension, "certificate_allowance": res.certificate_allowance,
			"cost_of_living": res.cost_of_living, "gross_pension": res.gross_pension,
			"monthly_tax": res.monthly_tax, "net_pension": res.net_pension,
			"end_of_service_bonus": res.end_of_service_bonus, "warnings": res.warnings}
