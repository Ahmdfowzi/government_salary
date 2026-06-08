# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Payroll Account Mapping (Single) — component → account-code map for the
proposal-only accounting journal export (Phase 4 M15).

Holds free-text account codes (this app has no Chart of Accounts / GL). The
mapping is read-only configuration; it is NEVER used to post ledger entries — the
journal export only proposes balanced rows.
"""

from frappe.model.document import Document


class PayrollAccountMapping(Document):
	pass
