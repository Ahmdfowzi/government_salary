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
V4. on_submit -> apply to profile + write Salary Calculation Log; no double-apply.
"""

from frappe.model.document import Document


class AnnualIncrementRequest(Document):
	def validate(self):
		# TODO(Phase 2): enforce V1-V3 via the increment service.
		pass

	def on_submit(self):
		# TODO(Phase 2): apply increment to the profile + write audit log (V4).
		pass
