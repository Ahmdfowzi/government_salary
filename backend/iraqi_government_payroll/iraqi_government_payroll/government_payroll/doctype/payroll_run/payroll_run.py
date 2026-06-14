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

	# --- Governance audit log (Phase 3 M5) --- #

	def _log_event(self, action, from_state):
		"""Insert one immutable governance event recording `action` (from_state ->
		current workflow_state). Failure aborts the transition loudly: a state
		change is never allowed to persist without its audit event.
		"""
		payload = governance.build_event(
			action, from_state, self.workflow_state,
			frappe.session.user, frappe.utils.now())
		payload["payroll_run"] = self.name
		try:
			frappe.get_doc(payload).insert(ignore_permissions=True)
		except Exception as exc:
			frappe.throw(
				f"Could not record governance audit event for '{action}'; "
				f"transition aborted: {exc}")

	# --- Governance workflow (server-side only) --- #

	def _perform_calculation(self):
		"""Core calculation body shared by the synchronous and queued paths.

		Identical engine call + governance transition + audit event in both cases —
		no calculation logic lives here (it is `repository.run_payroll`). The caller
		is responsible for the role check; this assumes it is already authorized.
		"""
		from_state = self.workflow_state
		target = governance.ensure_can_calculate(self.workflow_state)
		repository.run_payroll(self)            # sets run_status + counts (+saves)
		self.workflow_state = target
		self.calculated_by = frappe.session.user
		self.calculated_on = frappe.utils.now()
		self.save()
		self._log_event("calculate", from_state)
		return self.workflow_state

	@frappe.whitelist()
	def calculate_run(self):
		"""Run the batch synchronously (build draft slips) and move to Calculated.

		Kept for small runs and programmatic use. Large runs should use
		`calculate_run_async` so they do not exceed the HTTP/gunicorn timeout.
		"""
		self._ensure_role("calculate")
		return self._perform_calculation()

	@frappe.whitelist()
	def calculate_run_async(self):
		"""Queue the calculation as a background job (`frappe.enqueue`).

		The role check and the calculable-state guard run synchronously so the caller
		gets an immediate error (e.g. on a locked/approved run) instead of a silent
		background failure. The run is marked Queued and the identical calculation
		logic runs in the worker via `jobs.run_calculation_job`. Poll
		`calculation_status` for progress. Immutable-snapshot behaviour is unchanged —
		the worker takes the same `repository.run_payroll` path as the sync method.
		"""
		self._ensure_role("calculate")
		# Validate the transition is allowed NOW (raises if locked/approved/etc.).
		governance.ensure_can_calculate(self.workflow_state)
		self.db_set("run_status", "Queued", update_modified=False)
		job = frappe.enqueue(
			"iraqi_government_payroll.services.payroll_engine.jobs.run_calculation_job",
			queue="long",
			timeout=7200,
			enqueue_after_commit=True,
			run_name=self.name,
			user=frappe.session.user,
		)
		return {
			"status": "queued",
			"run": self.name,
			"run_status": "Queued",
			"job_id": getattr(job, "id", None),
		}

	@frappe.whitelist()
	def submit_for_review(self):
		self._ensure_role("submit_for_review")
		from_state = self.workflow_state
		self.workflow_state = governance.next_state("submit_for_review", self.workflow_state)
		self.reviewed_by = frappe.session.user
		self.reviewed_on = frappe.utils.now()
		self.save()
		self._log_event("submit_for_review", from_state)
		return self.workflow_state

	@frappe.whitelist()
	def approve_run(self):
		self._ensure_role("approve")
		from_state = self.workflow_state
		governance.ensure_can_approve(self.workflow_state, self.error_count)
		self.workflow_state = governance.APPROVED
		self.approved_by = frappe.session.user
		self.approved_on = frappe.utils.now()
		self.save()
		self._log_event("approve", from_state)
		return self.workflow_state

	@frappe.whitelist()
	def submit_run(self):
		self._ensure_role("submit")
		from_state = self.workflow_state
		self.workflow_state = governance.next_state("submit", self.workflow_state)
		self.submitted_by = frappe.session.user
		self.submitted_on = frappe.utils.now()
		self.save()
		self._log_event("submit", from_state)
		return self.workflow_state

	@frappe.whitelist()
	def cancel_run(self):
		self._ensure_role("cancel")
		from_state = self.workflow_state
		self.workflow_state = governance.next_state("cancel", self.workflow_state)
		self.save()
		self._log_event("cancel", from_state)
		return self.workflow_state

	# --- Locking & historical integrity (Phase 3 M3) --- #

	@frappe.whitelist()
	def lock_run(self):
		"""Lock a Submitted run -> immutable historical record (Administrator only)."""
		self._ensure_role("lock")
		from_state = self.workflow_state
		self.workflow_state = governance.ensure_can_lock(self.workflow_state)
		self.locked_by = frappe.session.user
		self.locked_on = frappe.utils.now()
		self.save()
		self._log_event("lock", from_state)
		return self.workflow_state

	@frappe.whitelist()
	def unlock_run(self):
		"""Unlock a Locked run back to Submitted — Payroll Administrator only, audited."""
		self._ensure_role("unlock")
		from_state = self.workflow_state
		self.workflow_state = governance.ensure_can_unlock(self.workflow_state)
		self.unlocked_by = frappe.session.user
		self.unlocked_on = frappe.utils.now()
		self.save()
		self._log_event("unlock", from_state)
		return self.workflow_state

	# --- Reporting helpers --- #

	# NOTE: do NOT name this `is_locked` — that shadows frappe.model.document.
	# Document.is_locked (a property used by Document.check_if_locked() on every
	# save), which made check_if_locked() mis-fire and break every save.
	def is_run_locked(self):
		return governance.is_locked(self.workflow_state)

	def is_historical_period(self):
		"""A locked run is a finalized, immutable historical period."""
		return self.is_run_locked()
