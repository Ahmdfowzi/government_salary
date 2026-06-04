# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Employee Payroll Profile — per-employee payroll state.

Purpose
-------
The salary "profile" of a single government employee: which law/scale applies,
current grade & stage, qualification, family/location attributes and the
increment/promotion timeline. This is the primary INPUT record the payroll,
increment, promotion and pension engines read from.

Relationships
-------------
- many -> 1 :class:`Government Rule Set` (field ``rule_set``)
- 1 -> many :class:`Annual Increment Request`
- 1 -> many :class:`Promotion Request`
- 1 -> many :class:`Pension Calculation`
- referenced by :class:`Payroll Calculation Snapshot`

(Phase 2 may link ``employee_number`` to an HRMS ``Employee`` master.)

Validation rules (Phase 2)
--------------------------
V1. employee_number unique (enforced by autoname).
V2. (current_grade, current_stage) must exist in the active scale of rule_set.
V3. eligible_children_count clamped to the legal max (loaded as data, e.g. 4).
V4. basic_salary is system-resolved and must not be hand-edited.
V5. next_increment_date / next_promotion_eligible_date derived, not free-typed.
"""

from frappe.model.document import Document


class GovernmentEmployeePayrollProfile(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V5 and resolve basic_salary from the scale.
		pass
