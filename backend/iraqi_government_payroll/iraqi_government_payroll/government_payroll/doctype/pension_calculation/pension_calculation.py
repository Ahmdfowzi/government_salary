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

from frappe.model.document import Document


class PensionCalculation(Document):
	def validate(self):
		# TODO(Phase 2): run the pension service and set computed fields (V1-V3).
		pass

	def on_submit(self):
		# TODO(Phase 2): write audit log (V4).
		pass
