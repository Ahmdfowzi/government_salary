# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Annual Increment Request — workflow document to apply a yearly increment.

Purpose
-------
Captures and approves a single annual increment (one stage up) for an employee.
The new stage/salary/amount are COMPUTED by the increment service (backend
only) — never typed by users — and applied to the profile on final approval.

Workflow (approval_status)
--------------------------
Draft -> HR Review -> Department Manager -> Finance Review -> Approved -> Applied
(Rejected is terminal.) Frappe ``docstatus`` submit/cancel guards the transition.

Relationships
-------------
- many -> 1 :class:`Government Employee Payroll Profile` (field ``employee_profile``)

Validation rules (Phase 2)
--------------------------
V1. Employee must be due (next_increment_date <= due_date).
V2. new_stage = current_stage + 1, bounded by the scale's top stage.
V3. Computed fields are server-set; reject client tampering.
V4. on_submit -> apply to profile + write Payroll Calculation Snapshot; no double-apply.
"""

import frappe
from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine import repository
from iraqi_government_payroll.services.security import access


class AnnualIncrementRequest(Document):
	def validate(self):
		from iraqi_government_payroll.services.increment.increment_service import (
			compute_increment, MAX_STAGE)
		from iraqi_government_payroll.services.payroll_engine.scale_resolver import resolve_grade_code

		# V3: clear server-computed output fields — only apply_increment (on_submit) may set these.
		self.new_stage = None
		self.new_salary = None
		self.increment_amount = None

		if not self.employee_profile:
			return

		profile = frappe.get_doc("Government Employee Payroll Profile", self.employee_profile)

		# V2: max-stage guard — increment requires promotion when at the ceiling.
		if int(profile.current_stage or 0) >= MAX_STAGE:
			frappe.throw(
				f"الموظف في المرحلة القصوى ({MAX_STAGE}) ولا يمكن منحه علاوة سنوية — "
				f"يُشترط الترقية أولاً. "
				f"(Employee is at maximum stage {MAX_STAGE}: promotion required before increment.)")

		# V1: eligibility check against the increment rule (only when due_date is provided).
		if self.due_date:
			gc = resolve_grade_code(
				profile.get("grade") or profile.get("grade_code"), profile.get("current_grade"))
			rule = (frappe.get_doc("Annual Increment Rule", profile.rule_set).as_dict()
					if profile.rule_set
					and frappe.db.exists("Annual Increment Rule", profile.rule_set)
					else {})
			res = compute_increment(
				{"grade_code": gc, "current_stage": profile.current_stage,
				 "current_stage_date": str(profile.current_stage_date or "")},
				rule, str(self.due_date), rule_set=profile.rule_set)
			if not res.eligible:
				frappe.throw(
					"; ".join(res.warnings)
					or "الموظف غير مستحق للعلاوة السنوية في هذا التاريخ. "
					   "(Employee is not eligible for an increment on the given date.)")

	def on_submit(self):
		# Phase 5 M1: increment approval (submit) is a restricted action.
		try:
			access.ensure_allowed("approve_increment", frappe.get_roles(frappe.session.user))
		except access.AccessDenied as exc:
			frappe.throw(str(exc))
		# M6: apply the increment to the employee profile + write an immutable snapshot.
		repository.apply_increment(self)
