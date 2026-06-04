# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Salary Scale — the grade/stage basic-salary matrix for a law.

Purpose
-------
Holds the official stored salary table for one law version, as child rows of
type :class:`Government Salary Scale Detail`. This is the authoritative source
the payroll engine reads ``basic_salary`` from for a given (grade, stage).

Relationships
-------------
- many -> 1 :class:`Government Rule Set` (field ``rule_set``)
- 1 -> many :class:`Government Salary Scale Detail` (child table ``details``)

Validation rules (Phase 2)
--------------------------
V1. Only one scale may be ``is_active`` per linked law.
V2. No duplicate (grade, stage) rows inside ``details``.
V3. ``rule_set`` must be in status Active or Archived (not Draft) to activate.
"""

from frappe.model.document import Document


class GovernmentSalaryScale(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V3.
		pass
