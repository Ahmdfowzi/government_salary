# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Payroll Run Governance Event — immutable, append-only audit of the approval workflow.

One write-once record is inserted for every Payroll Run governance transition
(calculate / submit_for_review / approve / submit / cancel / lock / unlock),
capturing the action, the from -> to states, the acting user and a timestamp.

Unlike the single-slot ``*_by`` / ``*_on`` fields on the run itself (which a later
transition overwrites), these events accumulate, so the full approval history —
including unlock -> resubmit cycles — is preserved and tamper-evident.

Immutability follows the proven Payroll Calculation Snapshot pattern: no role has
``write`` or ``delete`` permission, and the controller additionally blocks edits
and deletions of an already-saved event at the application layer.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class PayrollRunGovernanceEvent(Document):
	def on_update(self):
		# Immutable: once persisted, a governance event may not be modified.
		if self.get_doc_before_save() is not None:
			frappe.throw(_("Payroll Run Governance Event is immutable and cannot be modified."))

	def on_trash(self):
		# Immutable: governance events are audit history and may not be deleted.
		frappe.throw(_("Payroll Run Governance Event is immutable and cannot be deleted."))
