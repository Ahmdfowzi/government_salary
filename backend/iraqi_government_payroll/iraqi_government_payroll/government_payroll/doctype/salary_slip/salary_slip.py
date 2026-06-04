# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Salary Slip — computed monthly salary result per employee.

M5: wired to the Net Salary Orchestrator. On validate, the slip's basic salary,
allowances, deductions and net are computed by the backend engines (active
salary + pension deduction + tax) and populated automatically. On submit, an
immutable Salary Slip snapshot is persisted. No approval workflow yet.

All figures are computed in Python; nothing is calculated in the frontend.
"""

from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine import repository


class SalarySlip(Document):
	def validate(self):
		# Populate computed fields from the engines (round_iqd applied at this boundary).
		repository.compute_salary_slip(self)

	def on_submit(self):
		# Persist an immutable Salary Slip snapshot (reproducible record).
		repository.write_salary_slip_snapshot(self)
