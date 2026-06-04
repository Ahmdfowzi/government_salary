# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Salary Law — versioned header for a salary scale/law.

Purpose
-------
Represents one official, versioned salary law (e.g. SCALE_2015, SCALE_2008).
Every salary scale, qualification rule and allowance rule is anchored to a law
version so the engine can pick the correct rule set **by the payroll period
date** and support safe retroactive recalculation.

Relationships
-------------
- 1 -> many :class:`Government Salary Scale`
- 1 -> many :class:`Qualification Appointment Rule`

Validation rules (to be ENFORCED in Phase 2 — documented here only)
-------------------------------------------------------------------
V1. ``effective_to`` (when set) must be strictly after ``effective_from``.
V2. At most one law may be ``Active`` for any overlapping effective window.
V3. ``law_code`` is immutable once any scale references this law.
V4. Archiving a law that is referenced by an active profile raises a warning.
"""

from frappe.model.document import Document


class GovernmentSalaryLaw(Document):
	# Phase 1: design only. Validation hooks are intentionally left as stubs.
	def validate(self):
		# TODO(Phase 2): enforce V1-V4 described in the module docstring.
		pass
