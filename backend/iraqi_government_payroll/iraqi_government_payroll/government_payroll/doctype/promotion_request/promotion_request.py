# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Promotion Request — workflow document to promote an employee to a higher grade.

Purpose
-------
Captures and approves a grade promotion. Target grade, stage and salary are
COMPUTED by the promotion service (backend only) and applied to the profile on
final approval. Honors salary protection (new salary must not drop below old).

Workflow (approval_status)
--------------------------
Draft -> Eligibility Check -> Vacancy Check -> Manager Recommendation ->
Committee -> Higher Approval -> Finance Review -> Approved -> Applied
(Rejected is terminal.)

Relationships
-------------
- many -> 1 :class:`Government Employee Payroll Profile` (field ``employee_profile``)

Validation rules (Phase 2)
--------------------------
V1. years_in_grade must meet the law's minimum promotion duration.
V2. vacancy_available and manager recommendation required before Committee.
V3. proposed_stage chosen so new_salary >= old_salary (protected difference).
V4. on_submit -> apply to profile + write Payroll Calculation Snapshot.
"""

import frappe
from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine import repository
from iraqi_government_payroll.services.security import access


class PromotionRequest(Document):
	def validate(self):
		from iraqi_government_payroll.services.promotion.promotion_service import compute_promotion
		from iraqi_government_payroll.services.payroll_engine.repository import load_context
		from iraqi_government_payroll.services.payroll_engine.scale_resolver import (
			resolve_grade_code, get_active_scale)

		# V3: clear server-computed output fields — only apply_promotion (on_submit) may set these.
		self.to_grade_ref = None
		self.to_grade = None
		self.proposed_stage = None
		self.old_salary = None
		self.new_salary = None

		if not self.employee_profile:
			return

		# V2: vacancy and manager recommendation are prerequisites before approval.
		# Enforced at submit time (flags.in_submit) so DRAFT creation is not blocked.
		if self.flags.in_submit:
			if not self.vacancy_available:
				frappe.throw(
					"يُشترط توفر شاغر وظيفي لتقديم طلب الترقية. "
					"(Vacancy must be confirmed available before submitting a promotion request.)")
			if not self.direct_manager_recommendation:
				frappe.throw(
					"يُشترط توصية المدير المباشر لتقديم طلب الترقية. "
					"(Direct manager recommendation is required before submitting a promotion request.)")

		# V1: years_in_grade eligibility check via the promotion service.
		# Run at submit time so the engine verifies the legal minimum duration.
		if self.flags.in_submit:
			profile = frappe.get_doc("Government Employee Payroll Profile", self.employee_profile)
			gc = resolve_grade_code(
				profile.get("grade") or profile.get("grade_code"), profile.get("current_grade"))
			promotion_rule = (frappe.get_doc("Promotion Rule", profile.rule_set).as_dict()
							  if profile.rule_set
							  and frappe.db.exists("Promotion Rule", profile.rule_set)
							  else {})
			scale = get_active_scale(load_context().scales, profile.rule_set)
			effective_date = frappe.utils.today()
			res = compute_promotion(
				{"grade_code": gc, "current_stage": profile.current_stage,
				 "current_grade_date": str(profile.current_grade_date or "")},
				promotion_rule, scale.get("details", []), effective_date,
				rule_set=profile.rule_set)
			if not res.eligible:
				frappe.throw(
					"; ".join(res.warnings)
					or "الموظف غير مستحق للترقية في هذا التاريخ. "
					   "(Employee is not eligible for promotion at this time.)")

	def on_submit(self):
		# Phase 5 M1: promotion approval (submit) is a restricted action.
		try:
			access.ensure_allowed("approve_promotion", frappe.get_roles(frappe.session.user))
		except access.AccessDenied as exc:
			frappe.throw(str(exc))
		# M6: apply the promotion to the employee profile + write an immutable snapshot.
		repository.apply_promotion(self)
