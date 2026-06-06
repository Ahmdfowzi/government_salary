# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""EmployeeTransfer — Permanent record of an employee transfer between entities/positions.

Phase 3 M2 lifecycle event. Created via the lifecycle service, which also updates
the employee profile. Records are permanent audit history and cannot be deleted.
Standard Frappe audit fields (owner/creation/modified_by/modified) apply.
"""

import frappe
from frappe.model.document import Document


class EmployeeTransfer(Document):
	def on_trash(self):
		frappe.throw("Lifecycle records are permanent history and cannot be deleted.")
