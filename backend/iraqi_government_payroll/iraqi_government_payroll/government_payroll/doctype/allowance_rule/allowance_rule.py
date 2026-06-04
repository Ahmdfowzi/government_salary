# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Allowance Rule — catalog of allowance/deduction components and their behavior.

Purpose
-------
Single source of truth for every salary component (certificate, position, risk,
craft, family, geographic, pension contribution, etc.): how it is calculated
(percentage vs fixed), what it is computed on (always Basic for percentages),
whether it counts toward the 200% allowance cap, and its validity window.

The engine NEVER hardcodes these — it reads active Allowance Rule rows for the
relevant context (Active salary vs Pension) and effective date.

Validation rules (Phase 2)
--------------------------
V1. component_code unique (enforced by autoname).
V2. If calculation_type == Percentage -> percentage required; if Fixed ->
    fixed_amount required.
V3. effective_to (when set) must be after effective_from.
V4. context == Pension components may only be referenced by Pension Calculation.
"""

from frappe.model.document import Document


class AllowanceRule(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V4.
		pass
