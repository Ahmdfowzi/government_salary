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

import frappe
from frappe.model.document import Document


class AllowanceRule(Document):
	def validate(self):
		# V1: component_code uniqueness is enforced by the DocType autoname — no extra check needed.

		# V2: required rate fields based on calculation_type.
		if self.calculation_type == "Percentage":
			if not self.percentage:
				frappe.throw(
					"نسبة الاحتساب مطلوبة عند اختيار نوع الاحتساب «نسبة مئوية». "
					"(percentage is required when calculation_type is 'Percentage'.)")
		elif self.calculation_type == "Fixed":
			if not self.fixed_amount:
				frappe.throw(
					"المبلغ الثابت مطلوب عند اختيار نوع الاحتساب «ثابت». "
					"(fixed_amount is required when calculation_type is 'Fixed'.)")

		# V3 and V4: no effective_from/effective_to fields on this DocType; context
		# restriction (V4) is enforced by the allowance service at calculation time.
