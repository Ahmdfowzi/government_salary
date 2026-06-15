# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Pension Calculation — retirement pension computation record (Law Article 21).

Purpose
-------
Stores the inputs and the engine-computed result of an employee's pension:
36-month average, accrual, 100% cap, certificate pension allowance, cost of
living top-up, tax and net, plus end-of-service bonus. All money fields are
COMPUTED by the pension service (backend only) and read-only on the form.

Relationships
-------------
- many -> 1 :class:`Government Employee Payroll Profile` (field ``employee_profile``)

Validation rules (Phase 2)
--------------------------
V1. approved_pension = min(initial_pension, last_functional_salary)  [100% cap].
V2. average_36_months must be backed by 36 months of functional-salary data.
V3. accrual_rate / cap / averaging months pulled from the pension rule, not typed.
V4. on_submit -> write immutable Payroll Calculation Snapshot entry.
"""

import frappe
from frappe.model.document import Document


class PensionCalculation(Document):
	def validate(self):
		from iraqi_government_payroll.services.pension.pension_service import (
			compute_retirement_pension, RetirementPensionInput)
		from iraqi_government_payroll.services.payroll_engine.repository import load_pension_rule_data

		if not self.employee_profile or not self.rule_set:
			return

		# V2: average_36_months must be a positive value (represents 36-month data).
		if not (self.average_36_months and float(self.average_36_months or 0) > 0):
			frappe.throw(
				"متوسط الراتب لآخر 36 شهراً مطلوب ويجب أن يكون أكبر من صفر. "
				"(average_36_months is required and must be greater than zero.)")

		try:
			pension_rule, cert_rules, brackets = load_pension_rule_data(self.rule_set)
		except Exception:
			frappe.throw(
				f"لا توجد قاعدة تقاعد لمجموعة القواعد «{self.rule_set}». "
				f"(No Pension Rule for rule set '{self.rule_set}'.)")

		# V3: pull accrual_rate from the rule — override any client-typed value.
		self.accrual_rate = pension_rule.get("accrual_rate")

		pin = RetirementPensionInput(
			avg36=float(self.average_36_months or 0),
			service_years=int(self.service_years or 0),
			extra_months=int(self.extra_months or 0),
			last_functional_salary=float(self.last_functional_salary or 0),
			last_full_salary=float(self.last_full_salary or 0),
			qualification=frappe.db.get_value(
				"Government Employee Payroll Profile", self.employee_profile, "qualification"),
			other_deductions=float(self.other_deductions or 0),
			rule_set=self.rule_set,
			period_date=str(self.calculation_date or frappe.utils.today()),
			cost_of_living_method=pension_rule.get("cost_of_living_method"),
			cost_of_living_value=pension_rule.get("cost_of_living_value"),
		)
		res = compute_retirement_pension(pin, pension_rule, cert_rules, brackets)

		# V1: approved_pension = min(initial_pension, last_functional_salary) [100% cap].
		# The engine already enforces this; mirror all computed fields to the document.
		self.initial_pension = res.initial_pension
		self.approved_pension = res.approved_pension
		self.certificate_allowance = res.certificate_allowance
		self.cost_of_living = res.cost_of_living
		self.gross_pension = res.gross_pension
		self.taxable_income = res.taxable_income
		self.legal_allowances = res.legal_allowances
		self.annual_tax = res.annual_tax
		self.monthly_tax = res.monthly_tax
		self.net_pension = res.net_pension
		self.end_of_service_bonus = res.end_of_service_bonus

	def on_submit(self):
		# V4: write an immutable Payroll Calculation Snapshot (idempotent).
		from iraqi_government_payroll.services.pension.pension_service import (
			compute_retirement_pension, RetirementPensionInput)
		from iraqi_government_payroll.services.payroll_engine.repository import load_pension_rule_data
		from iraqi_government_payroll.services.audit.audit_service import (
			build_retirement_pension_snapshot_payload, write_payload)

		if frappe.db.exists("Payroll Calculation Snapshot",
							{"employee_profile": self.employee_profile,
							 "calculation_type": "Retirement Pension",
							 "source_request": self.name}):
			return

		try:
			pension_rule, cert_rules, brackets = load_pension_rule_data(self.rule_set)
		except Exception:
			return

		pin = RetirementPensionInput(
			avg36=float(self.average_36_months or 0),
			service_years=int(self.service_years or 0),
			extra_months=int(self.extra_months or 0),
			last_functional_salary=float(self.last_functional_salary or 0),
			last_full_salary=float(self.last_full_salary or 0),
			qualification=frappe.db.get_value(
				"Government Employee Payroll Profile", self.employee_profile, "qualification"),
			other_deductions=float(self.other_deductions or 0),
			rule_set=self.rule_set,
			period_date=str(self.calculation_date or frappe.utils.today()),
			cost_of_living_method=pension_rule.get("cost_of_living_method"),
			cost_of_living_value=pension_rule.get("cost_of_living_value"),
		)
		res = compute_retirement_pension(pin, pension_rule, cert_rules, brackets)
		payload = build_retirement_pension_snapshot_payload(
			res, pension_input=pin, employee_profile=self.employee_profile)
		payload["source_request"] = self.name
		write_payload(payload)
