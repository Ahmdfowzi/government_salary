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

import frappe
from frappe.model.document import Document


class GovernmentSalaryScale(Document):
	def validate(self):
		if not self.is_active:
			return

		# V1: only one active scale per rule_set.
		if self.rule_set:
			existing = frappe.db.get_value(
				"Government Salary Scale",
				{"rule_set": self.rule_set, "is_active": 1, "name": ["!=", self.name or "__new__"]},
				"name")
			if existing:
				frappe.throw(
					f"سلم الرواتب «{existing}» نشط بالفعل لمجموعة القواعد «{self.rule_set}». "
					f"(Scale '{existing}' is already active for rule set '{self.rule_set}'.)")

		# V3: rule_set must be Active or Archived (not Draft) to activate a scale.
		if self.rule_set:
			rs_status = frappe.db.get_value("Government Rule Set", self.rule_set, "status")
			if rs_status == "Draft":
				frappe.throw(
					f"لا يمكن تفعيل سلم الرواتب لمجموعة قواعد في حالة المسودة «{self.rule_set}». "
					f"(Cannot activate a salary scale for a Draft rule set '{self.rule_set}'.)")

		# V2: no duplicate (grade_code, stage) rows.
		seen = set()
		for row in (self.details or []):
			key = (str(row.grade_code), int(row.stage or 0))
			if key in seen:
				frappe.throw(
					f"صف مكرر في سلم الرواتب: الدرجة «{row.grade_code}» المرحلة «{row.stage}». "
					f"(Duplicate row in salary scale: grade '{row.grade_code}' stage '{row.stage}'.)")
			seen.add(key)
