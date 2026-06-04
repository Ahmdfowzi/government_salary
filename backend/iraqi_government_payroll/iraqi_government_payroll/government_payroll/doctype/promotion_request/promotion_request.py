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

from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine import repository


class PromotionRequest(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V3 via the promotion service.
		pass

	def on_submit(self):
		# M6: apply the promotion to the employee profile + write an immutable snapshot.
		repository.apply_promotion(self)
