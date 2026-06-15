# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Rule Set — versioned container for one complete legal package.

Purpose
-------
The single versioning spine of the system. A Government Rule Set bundles every
legal rule that applies for a period (salary scale, qualification rules,
allowance rules, tax brackets, pension rule, promotion rule, increment rule,
geographic areas and the versioned legal parameters). The engine resolves ONE
rule set by the payroll-period date, then reads all members linked to it.

Evolved from the former "Government Salary Law" — generalized from a salary
scale version to a complete legal-package version.

Amendments
----------
Active rule sets are not edited in place; an amendment = clone -> new version ->
publish. This guarantees that a Payroll Calculation Snapshot which references a
rule set version is fully reproducible.

Relationships
-------------
- 1 -> many :class:`Rule Set Parameter` (child table ``parameters``)
- 1 -> many Salary Scale / Qualification Appointment Rule / Allowance Rule /
  Income Tax Bracket / Tax Allowance Rule / Pension Rule / Promotion Rule /
  Annual Increment Rule / Geographic Area  (all link back via ``rule_set``)

Validation rules (Phase 2)
--------------------------
V1. ``effective_to`` (when set) must be strictly after ``effective_from``.
V2. At most one rule set may be ``Active`` for any overlapping effective window.
V3. ``rule_set_code`` is immutable once any member rule references it.
V4. Archiving a rule set referenced by an active profile raises a warning.
"""

import frappe
from frappe.model.document import Document


def _ranges_overlap(f1, t1, f2, t2):
	"""Return True if date ranges [f1, t1] and [f2, t2] overlap. None means open-ended."""
	a_ends_after_b_starts = (t1 is None) or (f2 is None) or (str(f2) <= str(t1))
	b_ends_after_a_starts = (t2 is None) or (f1 is None) or (str(f1) <= str(t2))
	return a_ends_after_b_starts and b_ends_after_a_starts


class GovernmentRuleSet(Document):
	def validate(self):
		# V1: effective_to must be strictly after effective_from when both are set.
		if self.effective_to and self.effective_from:
			if str(self.effective_to) <= str(self.effective_from):
				frappe.throw(
					"تاريخ انتهاء الصلاحية يجب أن يكون بعد تاريخ البدء. "
					"(effective_to must be strictly after effective_from.)")

		# V2: at most one Active rule set per overlapping effective window.
		if self.status == "Active":
			others = frappe.get_all(
				"Government Rule Set",
				filters={"status": "Active", "name": ["!=", self.name or "__new__"]},
				fields=["name", "effective_from", "effective_to"])
			for other in others:
				if _ranges_overlap(
						self.effective_from, self.effective_to,
						other.get("effective_from"), other.get("effective_to")):
					frappe.throw(
						f"مجموعة القواعد «{other['name']}» نشطة وتتداخل مع نافذة السريان المحددة. "
						f"(Rule set '{other['name']}' is Active and overlaps this effective window.)")

		# V3: rule_set_code is immutable once member rules reference this document.
		if not self.is_new():
			old_code = frappe.db.get_value("Government Rule Set", self.name, "rule_set_code")
			if old_code and old_code != self.rule_set_code:
				referenced = (
					frappe.db.exists("Government Salary Scale", {"rule_set": self.name})
					or frappe.db.exists("Allowance Rule", {"rule_set": self.name})
					or frappe.db.exists("Pension Rule", {"rule_set": self.name}))
				if referenced:
					frappe.throw(
						f"رمز مجموعة القواعد «{old_code}» لا يمكن تغييره بعد ربط قواعد به. "
						f"(rule_set_code '{old_code}' is immutable once member rules reference it.)")

		# V4: archiving a rule set still referenced by active employee profiles: warn only.
		if self.status == "Archived" and self.name:
			active_count = frappe.db.count(
				"Government Employee Payroll Profile",
				{"rule_set": self.name, "employment_status": "Active"})
			if active_count:
				frappe.msgprint(
					f"تنبيه: {active_count} موظف نشط لا يزال يستخدم هذه المجموعة. "
					f"(Warning: {active_count} active employee profile(s) still reference this rule set.)",
					indicator="orange", alert=True)
