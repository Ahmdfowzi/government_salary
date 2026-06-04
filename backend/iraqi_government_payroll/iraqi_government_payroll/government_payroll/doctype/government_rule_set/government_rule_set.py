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

from frappe.model.document import Document


class GovernmentRuleSet(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V4 described in the module docstring.
		pass
