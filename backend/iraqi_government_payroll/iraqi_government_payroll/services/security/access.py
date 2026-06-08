# Copyright (c) 2026, Iraqi Government Payroll
"""Sensitive-action access control (Phase 5 M1) — PURE, no Frappe.

A small role matrix for the privileged operations the milestone protects, on top
of the DocType-level permissions and the existing Payroll Run governance RBAC
(Phase 3 M4). Pure so it is unit-testable without a bench; controllers/endpoints
read the user's roles and call ensure_allowed().

Covered here: increment approval, promotion approval, accounting journal export.
(Payroll Run lock/unlock stay governed by services/payroll_engine/governance.py,
extended in this milestone to also admit the Government Payroll Administrator.)
"""

# Roles
GOVERNMENT_PAYROLL_ADMINISTRATOR = "Government Payroll Administrator"
PAYROLL_ADMINISTRATOR = "Payroll Administrator"
PAYROLL_MANAGER = "Payroll Manager"
PAYROLL_OFFICER = "Payroll Officer"
HR_OFFICER = "HR Officer"
HR_USER = "HR User"
FINANCE_OFFICER = "Finance Officer"
FINANCE_USER = "Finance User"
AUDITOR = "Auditor"
READ_ONLY_USER = "Read Only User"
SYSTEM_MANAGER = "System Manager"

# Roles that always pass (full administrative access).
SUPERUSERS = frozenset({SYSTEM_MANAGER, GOVERNMENT_PAYROLL_ADMINISTRATOR})

# action -> roles permitted (in addition to the SUPERUSERS above).
SENSITIVE_ACTIONS = {
	"approve_increment": frozenset({PAYROLL_ADMINISTRATOR, PAYROLL_MANAGER}),
	"approve_promotion": frozenset({PAYROLL_ADMINISTRATOR, PAYROLL_MANAGER}),
	"export_accounting_journal": frozenset({
		PAYROLL_ADMINISTRATOR, PAYROLL_MANAGER, FINANCE_OFFICER, FINANCE_USER}),
}


class AccessDenied(Exception):
	"""Raised when the current roles may not perform a sensitive action."""


def is_allowed(action, user_roles):
	"""Pure predicate: may any of `user_roles` perform `action`?

	Unknown actions fail closed; SUPERUSERS always pass a known action.
	"""
	if action not in SENSITIVE_ACTIONS:
		return False
	roles = set(user_roles or ())
	if roles & SUPERUSERS:
		return True
	return bool(SENSITIVE_ACTIONS[action] & roles)


def ensure_allowed(action, user_roles):
	"""Raise AccessDenied unless `user_roles` may perform `action`."""
	if action not in SENSITIVE_ACTIONS:
		raise AccessDenied(f"Unknown protected action: {action}")
	if not is_allowed(action, user_roles):
		allowed = ", ".join(sorted(SENSITIVE_ACTIONS[action] | SUPERUSERS))
		raise AccessDenied(
			f"You are not authorized to '{action}'. Requires one of: {allowed}.")
	return True
