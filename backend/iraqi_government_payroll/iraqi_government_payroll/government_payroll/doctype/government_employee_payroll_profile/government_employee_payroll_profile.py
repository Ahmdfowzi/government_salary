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
	resolve_basic_salary,
)
from iraqi_government_payroll.services.family import family_service

_FAMILY_SUMMARY_FIELDS = (
	"spouse_count", "children_count", "eligible_children_count", "dependents_count",
	"eligible_dependents_count", "disabled_dependents_count",
	"employed_dependents_count", "student_dependents_count",
)


class GovernmentEmployeePayrollProfile(Document):
	def validate(self):
		# Phase 5 M4.1: keep the new `grade` Link and the deprecated `grade_code`
		# mirror in sync, and validate that (grade, stage) exists in the active scale.
		self._sync_grade_fields()
		self._validate_scale_placement()
		# Resolve basic_salary from the active salary scale so the profile always
		# reflects the current scale value (read-only; engine recomputes at payroll time).
		self._resolve_and_set_basic_salary()
		# Phase 5 M7: recompute dependent ages / eligibility / summary counts so they
		# are current whenever family data changes (and ready to snapshot at payroll).
		self._recompute_family()

	def before_save(self):
		# Belt-and-suspenders: ensure basic_salary is current even on programmatic saves
		# (e.g. apply_increment / apply_promotion call profile.save() directly).
		self._resolve_and_set_basic_salary()

	def _family_config(self):
		"""Eligibility thresholds from Government Payroll Settings (configurable;
		no legal AMOUNTS — those live in Allowance Rule / Tax Rule)."""
		cfg = {}
		try:
			s = frappe.get_single("Government Payroll Settings")
			if s.get("dependent_child_max_age"):
				cfg["child_max_age"] = int(s.dependent_child_max_age)
			if s.get("dependent_student_max_age"):
				cfg["student_max_age"] = int(s.dependent_student_max_age)
			if s.get("dependent_income_threshold") is not None:
				cfg["dependent_income_threshold"] = float(s.dependent_income_threshold)
		except Exception:
			pass            # fall back to family_service defaults
		return cfg

	def _recompute_family(self):
		members = [m.as_dict() for m in (self.get("family_members") or [])]
		today = frappe.utils.nowdate() if hasattr(frappe.utils, "nowdate") else None
		result = family_service.summarize(members, as_of=today, config=self._family_config())
		# write computed age + eligibility back onto each child row (read-only fields)
		for row, enriched in zip(self.get("family_members") or [], result["members"]):
			row.age = enriched["age"]
			row.eligible_for_family_allowance = enriched["eligible_for_family_allowance"]
		# write the summary counts onto the profile
		for field in _FAMILY_SUMMARY_FIELDS:
			self.set(field, result["summary"][field])

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
		# appointment grade: Link is authoritative, legacy Int is a synced mirror
		if self.appointment_grade_ref and not self.appointment_grade \
				and str(self.appointment_grade_ref).isdigit():
			self.appointment_grade = int(self.appointment_grade_ref)
		elif self.appointment_grade and not self.appointment_grade_ref:
			self.appointment_grade_ref = str(self.appointment_grade)

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

	def _resolve_and_set_basic_salary(self):
		"""Resolve basic_salary from the active salary scale and store it on the profile.

		Skipped during install/migrate and when required fields are missing, so it
		never blocks seeding. Placement validity is guaranteed by _validate_scale_placement
		which runs first; this method only looks up the matching salary value.
		"""
		if frappe.flags.in_install or frappe.flags.in_migrate:
			return
		grade = self.grade or self.grade_code
		if not (grade and self.current_stage and self.rule_set):
			return
		salary = resolve_basic_salary(
			rule_set=self.rule_set,
			grade=grade,
			current_stage=self.current_stage,
			grade_ref=self.grade,           # profile.grade (Link) mirrors scale detail grade_ref
			current_grade=self.current_grade,
		)
		self.basic_salary = salary
