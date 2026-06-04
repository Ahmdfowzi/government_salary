# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Payroll Run — batch that builds draft Salary Slips for a period.

M7: the batch engine lives in services. Call `run_batch()` to execute (e.g. from
bench console or a future button). M7 does not auto-run on save, does not submit
slips, and adds no approval workflow.
"""

import frappe
from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine import repository


class PayrollRun(Document):
	@frappe.whitelist()
	def run_batch(self):
		"""Process eligible employees into draft Salary Slips and tally results."""
		return repository.run_payroll(self)
