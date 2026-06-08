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

import frappe
from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine.scale_resolver import (
	scale_has_grade_stage,
)


class GovernmentEmployeePayrollProfile(Document):
	def validate(self):
		# Phase 5 M4.1: keep the new `grade` Link and the deprecated `grade_code`
		# mirror in sync, and validate that (grade, stage) exists in the active scale.
		self._sync_grade_fields()
		self._validate_scale_placement()

	def _sync_grade_fields(self):
		"""Grade (Link) is authoritative; grade_code (deprecated) mirrors it so
		slips / snapshots / reports that still read grade_code keep working. Either
		field may be supplied (UI sets grade; legacy inserts set grade_code)."""
		if self.grade and not self.grade_code:
			self.grade_code = self.grade
		elif self.grade_code and not self.grade:
			self.grade = self.grade_code
		elif self.grade and self.grade_code and self.grade != self.grade_code:
			self.grade_code = self.grade          # Link wins on conflict
		# keep the legacy Int populated for regular grades (display only)
		code = self.grade or self.grade_code
		if code and str(code).isdigit():
			self.current_grade = int(code)

	def _validate_scale_placement(self):
		"""Reject a (grade, stage) that does not exist in the active rule-set scale
		(e.g. grade 7 stage 99). Skipped during install/migrate and when the scale
		is not loaded, so it never blocks seeding or backfill."""
		if frappe.flags.in_install or frappe.flags.in_migrate:
			return
		grade = self.grade or self.grade_code
		if not (grade and self.current_stage and self.rule_set):
			return
		scale = frappe.db.get_value(
			"Government Salary Scale", {"rule_set": self.rule_set, "is_active": 1}, "name"
		) or frappe.db.get_value("Government Salary Scale", {"rule_set": self.rule_set}, "name")
		if not scale:
			return                                 # no scale loaded -> don't block
		details = frappe.get_all(
			"Government Salary Scale Detail", filters={"parent": scale},
			fields=["grade_code", "stage"])
		if not scale_has_grade_stage(details, grade, self.current_stage):
			frappe.throw(
				f"Invalid salary placement: grade '{grade}' stage '{self.current_stage}' "
				f"does not exist in the active salary scale of rule set '{self.rule_set}'.")
