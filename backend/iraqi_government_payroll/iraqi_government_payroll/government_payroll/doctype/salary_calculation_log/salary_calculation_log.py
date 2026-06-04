# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Salary Calculation Log — immutable audit trail for every calculation.

Purpose
-------
A write-once record produced by the engine for each active-salary, increment,
promotion, pension or tax computation. It captures the legal context (law,
grade, stage, qualification, decision), the totals, a per-component breakdown
(child table) and full input/output JSON snapshots — so any figure can be
reproduced and traced to its source rule.

Immutability
------------
No role has ``write`` or ``delete`` permission; records are created only by the
backend services. The controller additionally blocks edits after insert.

Relationships
-------------
- many -> 1 :class:`Government Employee Payroll Profile` (field ``employee_profile``)
- 1 -> many :class:`Salary Calculation Log Line` (child table ``lines``)

Validation rules (Phase 2)
--------------------------
V1. Reject any update to an existing log (raise on ``on_update`` when not new).
V2. net_amount == gross_amount - total_deductions.
V3. Every line must carry a ``source_rule`` and ``reason_text``.
"""

from frappe.model.document import Document


class SalaryCalculationLog(Document):
	def on_update(self):
		# TODO(Phase 2): enforce immutability — disallow edits to existing logs (V1).
		pass
