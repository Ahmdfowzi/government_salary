# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Qualification Appointment Rule — certificate -> starting grade/stage mapping.

Purpose
-------
Defines, per law version, the starting grade/stage an employee is appointed to
based on their academic qualification (and optional specialization), plus the
certificate allowance percentage that qualification grants on the active salary.

Relationships
-------------
- many -> 1 :class:`Government Rule Set` (field ``rule_set``)
- consumed by the appointment / employee-profile setup flow

Validation rules (Phase 2)
--------------------------
V1. (rule_set, qualification_level, specialization) must be unique.
V2. starting_grade / starting_stage must exist in the law's active scale.
V3. certificate_allowance_percentage in [0, 100].

NOTE: Legal percentages and starting grades are NOT hardcoded in Phase 1 — they
are loaded as data/fixtures once the official numbers are confirmed (Phase 2).
"""

import frappe
from frappe.model.document import Document


class QualificationAppointmentRule(Document):
	def validate(self):
		# Phase 5 M4.2: starting_grade_ref (Link -> Government Grade) is authoritative;
		# the legacy Int starting_grade is kept as a synced mirror.
		self._sync_starting_grade()

		# V3: certificate_allowance_percentage must be in [0, 100].
		pct = self.certificate_allowance_percentage
		if pct is not None and not (0 <= float(pct) <= 100):
			frappe.throw(
				"نسبة علاوة الشهادة يجب أن تكون بين 0 و 100. "
				"(certificate_allowance_percentage must be in the range [0, 100].)")

		# V1: (rule_set, qualification_level, specialization) must be unique.
		if self.rule_set and self.qualification_level:
			filters = {
				"rule_set": self.rule_set,
				"qualification_level": self.qualification_level,
				"name": ["!=", self.name or "__new__"],
			}
			if self.specialization:
				filters["specialization"] = self.specialization
			else:
				filters["specialization"] = ["in", [None, ""]]
			if frappe.db.exists("Qualification Appointment Rule", filters):
				frappe.throw(
					"توجد قاعدة تعيين بنفس مجموعة القواعد والمؤهل العلمي والتخصص. "
					"(A Qualification Appointment Rule already exists for this "
					"rule_set + qualification_level + specialization combination.)")

		# V2: starting_grade / starting_stage must exist in the law's active scale.
		if self.rule_set and self.starting_grade_ref and self.starting_stage:
			from iraqi_government_payroll.services.payroll_engine.scale_resolver import (
				scale_has_grade_stage)
			scale_name = (
				frappe.db.get_value(
					"Government Salary Scale",
					{"rule_set": self.rule_set, "is_active": 1}, "name")
				or frappe.db.get_value(
					"Government Salary Scale", {"rule_set": self.rule_set}, "name"))
			if scale_name:
				details = frappe.get_all(
					"Government Salary Scale Detail",
					filters={"parent": scale_name},
					fields=["grade_code", "stage", "basic_salary"])
				if not scale_has_grade_stage(details, str(self.starting_grade_ref),
											 int(self.starting_stage)):
					frappe.throw(
						f"الدرجة «{self.starting_grade_ref}» والمرحلة «{self.starting_stage}» "
						f"غير موجودة في سلم الرواتب الفعّال لمجموعة القواعد «{self.rule_set}». "
						f"(Starting grade '{self.starting_grade_ref}' stage '{self.starting_stage}' "
						f"is not in the active salary scale for rule set '{self.rule_set}'.)")

	def _sync_starting_grade(self):
		if self.starting_grade_ref and not self.starting_grade \
				and str(self.starting_grade_ref).isdigit():
			self.starting_grade = int(self.starting_grade_ref)
		elif self.starting_grade and not self.starting_grade_ref:
			self.starting_grade_ref = str(self.starting_grade)
