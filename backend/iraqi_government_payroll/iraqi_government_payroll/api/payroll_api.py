# Copyright (c) 2026, Iraqi Government Payroll
"""Whitelisted REST endpoints consumed by the Next.js frontend.

All calculations happen on the backend; the frontend only reads/writes data and
triggers these endpoints. Phase 1 declares the surface; logic lands in Phase 2.
"""

import frappe

from iraqi_government_payroll.services.payroll_engine import governance


@frappe.whitelist()
def calculate_active_salary(profile, period_date):
	"""Trigger the payroll engine for one employee profile."""
	raise NotImplementedError("Phase 2: wire to services.payroll_engine.engine")


@frappe.whitelist()
def evaluate_increment(profile):
	"""Preview the annual increment for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.increment.increment_service")


@frappe.whitelist()
def evaluate_promotion(profile):
	"""Preview a promotion for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.promotion.promotion_service")


@frappe.whitelist()
def compute_pension(profile, calculation_date):
	"""Compute the pension for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.pension.pension_service")


# --- Payroll Run governance (Phase 3 M6) --- #
# Thin REST surface over the Payroll Run controller's governance transitions. Each
# action maps to a controller method that ALREADY enforces role (M4) and writes an
# immutable audit event (M5); these endpoints only route — no authorization, state
# machine or audit logic is duplicated here.

_ACTION_METHODS = {
	"calculate": "calculate_run",
	"submit_for_review": "submit_for_review",
	"approve": "approve_run",
	"submit": "submit_run",
	"cancel": "cancel_run",
	"lock": "lock_run",
	"unlock": "unlock_run",
}

_AUDIT_FIELDS = (
	"calculated_by", "calculated_on", "reviewed_by", "reviewed_on",
	"approved_by", "approved_on", "submitted_by", "submitted_on",
	"locked_by", "locked_on", "unlocked_by", "unlocked_on",
)


@frappe.whitelist()
def run_governance_action(run, action):
	"""Perform one governance transition on a Payroll Run.

	`action` is one of GOVERNANCE_ACTIONS. The matching controller method enforces
	role + writes the audit event + transitions state; this only dispatches.
	Returns the new workflow_state and the actions now available to the caller.
	"""
	if action not in _ACTION_METHODS:
		frappe.throw(f"Unknown payroll run action: {action}")
	doc = frappe.get_doc("Payroll Run", run)
	getattr(doc, _ACTION_METHODS[action])()
	return {
		"name": doc.name,
		"workflow_state": doc.workflow_state,
		"allowed_actions": governance.available_actions(
			doc.workflow_state, frappe.get_roles(frappe.session.user)),
	}


@frappe.whitelist()
def get_run_governance(run):
	"""Read-only governance view of a Payroll Run: current state, the actions the
	caller may take now, the per-transition audit fields, and the immutable event
	trail (oldest first)."""
	doc = frappe.get_doc("Payroll Run", run)
	roles = frappe.get_roles(frappe.session.user)
	events = frappe.get_all(
		"Payroll Run Governance Event",
		filters={"payroll_run": run},
		fields=["action", "from_state", "to_state", "actor", "event_timestamp"],
		order_by="creation asc")
	return {
		"name": doc.name,
		"workflow_state": doc.workflow_state,
		"run_status": doc.get("run_status"),
		"error_count": doc.get("error_count"),
		"allowed_actions": governance.available_actions(doc.workflow_state, roles),
		"audit": {f: doc.get(f) for f in _AUDIT_FIELDS},
		"events": events,
	}
