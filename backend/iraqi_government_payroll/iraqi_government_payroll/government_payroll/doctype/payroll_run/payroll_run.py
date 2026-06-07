# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Payroll Run — batch executor + governance/approval workflow.

The calculation batch lives in services; this controller adds a server-side
approval lifecycle on top of it (no engine changes):

    Draft -> Calculated -> Under Review -> Approved -> Submitted
                      \-> Cancelled (any pre-submit state)

Protection rules (server-enforced):
  * cannot recalculate once Approved / Submitted / Cancelled
  * cannot approve while the run has blocking errors (error_count > 0)
  * cannot delete a Submitted run
  * Payroll Calculation Snapshots remain immutable (enforced in that DocType)

Audit fields (calculated/reviewed/approved/submitted _by/_on) are stamped by the
server only. Re-invoking a transition from a state it is not allowed from raises,
so the methods are safe against accidental double-calls.
"""

import frappe
from frappe.model.document import Document

from iraqi_government_payroll.services.payroll_engine import repository, governance


class PayrollRun(Document):
	def on_trash(self):
		# Block deletion of finalized runs. Explicit check (Locked / Submitted /
		# submitted docstatus) plus the governance guard, raising a ValidationError
		# so the delete is always aborted.
		state = self.workflow_state or governance.DRAFT
		if state in (governance.SUBMITTED, governance.LOCKED) or int(self.docstatus or 0) == 1:
			frappe.throw(f"Cannot delete a payroll run in '{state}' state.")
		governance.ensure_can_delete(state)

	# --- Authorization (segregation of duties) --- #

	def _ensure_role(self, action):
		"""Server-side guard: the current user must hold a role permitting `action`."""
		governance.ensure_role_allowed(action, frappe.get_roles(frappe.session.user))

	# --- Governance workflow (server-side only) --- #

	@frappe.whitelist()
	def calculate_run(self):
		"""Run the batch (build draft slips) and move to Calculated."""
		self._ensure_role("calculate")
		target = governance.ensure_can_calculate(self.workflow_state)
		repository.run_payroll(self)            # sets run_status + counts (+saves)
		self.workflow_state = target
		self.calculated_by = frappe.session.user
		self.calculated_on = frappe.utils.now()
		self.save()
		return self.workflow_state

	@frappe.whitelist()
	def submit_for_review(self):
		self._ensure_role("submit_for_review")
		self.workflow_state = governance.next_state("submit_for_review", self.workflow_state)
		self.reviewed_by = frappe.session.user
		self.reviewed_on = frappe.utils.now()
		self.save()
		return self.workflow_state

	@frappe.whitelist()
	def approve_run(self):
		self._ensure_role("approve")
		governance.ensure_can_approve(self.workflow_state, self.error_count)
		self.workflow_state = governance.APPROVED
		self.approved_by = frappe.session.user
		self.approved_on = frappe.utils.now()
		self.save()
		return self.workflow_state

	@frappe.whitelist()
	def submit_run(self):
		self._ensure_role("submit")
		self.workflow_state = governance.next_state("submit", self.workflow_state)
		self.submitted_by = frappe.session.user
		self.submitted_on = frappe.utils.now()
		self.save()
		return self.workflow_state

	@frappe.whitelist()
	def cancel_run(self):
		self._ensure_role("cancel")
		self.workflow_state = governance.next_state("cancel", self.workflow_state)
		self.save()
		return self.workflow_state

	# --- Locking & historical integrity (Phase 3 M3) --- #

	@frappe.whitelist()
	def lock_run(self):
		"""Lock a Submitted run -> immutable historical record (Administrator only)."""
		self._ensure_role("lock")
		self.workflow_state = governance.ensure_can_lock(self.workflow_state)
		self.locked_by = frappe.session.user
		self.locked_on = frappe.utils.now()
		self.save()
		return self.workflow_state

	@frappe.whitelist()
	def unlock_run(self):
		"""Unlock a Locked run back to Submitted — Payroll Administrator only, audited."""
		self._ensure_role("unlock")
		self.workflow_state = governance.ensure_can_unlock(self.workflow_state)
		self.unlocked_by = frappe.session.user
		self.unlocked_on = frappe.utils.now()
		self.save()
		return self.workflow_state

	# --- Reporting helpers --- #

	def is_locked(self):
		return governance.is_locked(self.workflow_state)

	def is_historical_period(self):
		"""A locked run is a finalized, immutable historical period."""
		return self.is_locked()
