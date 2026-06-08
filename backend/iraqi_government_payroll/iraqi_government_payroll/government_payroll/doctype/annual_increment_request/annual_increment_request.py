# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Annual Increment Request — workflow document to apply a yearly increment.

Purpose
-------
Captures and approves a single annual increment (one stage up) for an employee.
The new stage/salary/amount are COMPUTED by the increment service (backend
only) — never typed by users — and applied to the profile on final approval.

Workflow (approval_status)
--------------------------
Draft -> HR Review -> Department Manager -> Finance Review -> Approved -> Applied
(Rejected is terminal.) Frappe ``docstatus`` submit/cancel guards the transition.

Relationships
-------------
- many -> 1 :class:`Government Employee Payroll Profile` (field ``employee_profile``)

Validation rules (Phase 2)
--------------------------
V1. Employee must be due (next_increment_date <= due_date).
V2. new_stage = current_stage + 1, bounded by the scale's top stage.
V3. Computed fields are server-set; reject client tampering.
V4. on_submit -> apply to profile + write Payroll Calculation Snapshot; no double-apply.
"""

import frappe
from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine import repository
from iraqi_government_payroll.services.security import access


class AnnualIncrementRequest(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V3 via the increment service.
		pass

	def on_submit(self):
		# Phase 5 M1: increment approval (submit) is a restricted action.
		try:
			access.ensure_allowed("approve_increment", frappe.get_roles(frappe.session.user))
		except access.AccessDenied as exc:
			frappe.throw(str(exc))
		# M6: apply the increment to the employee profile + write an immutable snapshot.
		repository.apply_increment(self)
