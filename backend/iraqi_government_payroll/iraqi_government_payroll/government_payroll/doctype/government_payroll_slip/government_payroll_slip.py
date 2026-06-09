# Copyright (c) 2026, Iraqi Government Payroll
"""Government Payroll Slip — printable Iraqi government salary slip (مفردات راتب).

GENERATED, never calculated. It is assembled from the immutable Payroll
Calculation Snapshot (the source of truth for every amount) plus employee /
period / entity master data, by ``services/slip/slip_builder.build_slip`` and the
``api/slip_api`` wiring. This controller stores no business logic — the engine is
never touched here.
"""

from frappe.model.document import Document


class GovernmentPayrollSlip(Document):
	pass
