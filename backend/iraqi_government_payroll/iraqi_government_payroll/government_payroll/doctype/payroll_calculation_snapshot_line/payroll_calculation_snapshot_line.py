# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Payroll Calculation Snapshot Line — child of :class:`Payroll Calculation Snapshot`.

One fully-explained component of a calculation: amount, basis, rate, whether the
200% cap was applied, the source rule and a human-readable reason. This is what
makes every figure on a payslip auditable back to its legal source.
"""

from frappe.model.document import Document


class PayrollCalculationSnapshotLine(Document):
	pass
