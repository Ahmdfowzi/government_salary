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
- many -> 1 :class:`Government Salary Law` (field ``salary_law``)
- consumed by the appointment / employee-profile setup flow

Validation rules (Phase 2)
--------------------------
V1. (salary_law, qualification_level, specialization) must be unique.
V2. starting_grade / starting_stage must exist in the law's active scale.
V3. certificate_allowance_percentage in [0, 100].

NOTE: Legal percentages and starting grades are NOT hardcoded in Phase 1 — they
are loaded as data/fixtures once the official numbers are confirmed (Phase 2).
"""

from frappe.model.document import Document


class QualificationAppointmentRule(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V3.
		pass
