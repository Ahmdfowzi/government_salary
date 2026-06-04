# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Payroll Period — a payroll period (year/month) with a Draft -> Open -> Closed flow.

M7: validates the date range, year/month consistency, no duplicate period, and
the status transition.
"""

import frappe
from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine.payroll_period import (
	validate_period_dates, validate_status_transition, check_duplicate,
)


class PayrollPeriod(Document):
	def validate(self):
		validate_period_dates(self.year, self.month, self.start_date, self.end_date)

		# Duplicate detection (same year/month), excluding this record.
		existing = frappe.get_all(
			"Payroll Period",
			filters={"year": self.year, "month": self.month, "name": ["!=", self.name]},
			fields=["year", "month"])
		check_duplicate(self.year, self.month, [(r["year"], r["month"]) for r in existing])

		# Status flow Draft -> Open -> Closed.
		old = self.get_doc_before_save()
		old_status = old.status if old else None
		if old_status and old_status != self.status:
			validate_status_transition(old_status, self.status)
