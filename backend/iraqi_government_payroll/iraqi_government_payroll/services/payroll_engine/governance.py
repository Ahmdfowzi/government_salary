# Copyright (c) 2026, Iraqi Government Payroll
"""Payroll Run governance state machine + protection rules (pure, no Frappe).

Governs the approval lifecycle of a Payroll Run WITHOUT touching the calculation
engines. The state machine and guards are pure so they are unit-testable; the
Payroll Run controller wires them to Frappe (audit fields, save, on_trash).
"""

from .types import PayrollError

# Workflow states
DRAFT = "Draft"
CALCULATED = "Calculated"
UNDER_REVIEW = "Under Review"
APPROVED = "Approved"
SUBMITTED = "Submitted"
CANCELLED = "Cancelled"

WORKFLOW_STATES = [DRAFT, CALCULATED, UNDER_REVIEW, APPROVED, SUBMITTED, CANCELLED]

# action -> (set of states it may be performed FROM, resulting state)
TRANSITIONS = {
	"calculate":         ({DRAFT, CALCULATED, UNDER_REVIEW}, CALCULATED),
	"submit_for_review": ({CALCULATED}, UNDER_REVIEW),
	"approve":           ({UNDER_REVIEW}, APPROVED),
	"submit":            ({APPROVED}, SUBMITTED),
	"cancel":            ({DRAFT, CALCULATED, UNDER_REVIEW, APPROVED}, CANCELLED),
}


def next_state(action, current):
	"""Return the resulting state for `action` from `current`, or raise PayrollError."""
	if action not in TRANSITIONS:
		raise PayrollError(f"Unknown payroll run action: {action}")
	allowed_from, target = TRANSITIONS[action]
	cur = current or DRAFT
	if cur not in allowed_from:
		raise PayrollError(
			f"Cannot '{action}' a payroll run in state '{cur}'. "
			f"Allowed from: {', '.join(sorted(allowed_from))}.")
	return target


def ensure_can_calculate(current):
	"""Protection rule: cannot (re)calculate once Approved / Submitted / Cancelled."""
	cur = current or DRAFT
	if cur in (APPROVED, SUBMITTED, CANCELLED):
		raise PayrollError(f"Cannot recalculate a payroll run in '{cur}' state.")
	return next_state("calculate", cur)


def ensure_can_approve(current, error_count):
	"""Protection rule: approval requires Under Review and zero blocking errors."""
	target = next_state("approve", current)        # raises unless Under Review
	if int(error_count or 0) > 0:
		raise PayrollError(
			f"Cannot approve: payroll run has {int(error_count)} blocking error(s). "
			f"Resolve errors and recalculate before approval.")
	return target


def ensure_can_delete(current):
	"""Protection rule: a Submitted payroll run cannot be deleted."""
	if (current or DRAFT) == SUBMITTED:
		raise PayrollError("Cannot delete a submitted payroll run.")
	return True
