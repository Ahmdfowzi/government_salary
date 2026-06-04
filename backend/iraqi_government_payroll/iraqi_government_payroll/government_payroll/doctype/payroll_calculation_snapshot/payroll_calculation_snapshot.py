# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Payroll Calculation Snapshot — immutable, reproducible record of a calculation.

Purpose
-------
A write-once artifact produced by the engine for each active-salary, increment,
promotion, pension or tax computation. It pins the full reproducibility chain:

    reproduce(output) = engine(engine_version) x rule_set(version) x input_snapshot

so any figure can be re-derived and traced to its source rule. Evolved from the
former "Salary Calculation Log".

Immutability
------------
No role has ``write`` or ``delete`` permission. The controller additionally
blocks edits and deletions of an already-saved snapshot at the application
layer, so even privileged code paths cannot mutate history.

Relationships
-------------
- many -> 1 :class:`Government Rule Set` (field ``rule_set``)
- many -> 1 :class:`Government Employee Payroll Profile` (``employee_profile``)
- many -> 1 :class:`Salary Slip` (``salary_slip``) / :class:`Payroll Period`
- 1 -> many :class:`Payroll Calculation Snapshot Line` (child table ``lines``)

Validation rules (Phase 2)
--------------------------
V1. net_amount == gross_amount - total_deductions.
V2. Every line must carry a ``source_rule`` and ``reason_text``.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class PayrollCalculationSnapshot(Document):
	def on_update(self):
		# Immutable: once persisted, a snapshot may not be modified.
		if self.get_doc_before_save() is not None:
			frappe.throw(_("Payroll Calculation Snapshot is immutable and cannot be modified."))

	def on_trash(self):
		# Immutable: snapshots are audit history and may not be deleted.
		frappe.throw(_("Payroll Calculation Snapshot is immutable and cannot be deleted."))
