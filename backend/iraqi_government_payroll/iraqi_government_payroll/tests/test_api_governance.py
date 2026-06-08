# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 3 M6 payroll governance API (pure + fake-frappe, no bench).

Run:  python3 -m unittest test_api_governance -v
"""

import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine import governance as gov  # noqa: E402

OFFICER = gov.PAYROLL_OFFICER
MANAGER = gov.PAYROLL_MANAGER
ADMIN = gov.PAYROLL_ADMINISTRATOR
SYSMGR = gov.SYSTEM_MANAGER


# --------------------------- Pure available_actions --------------------------- #
class TestAvailableActions(unittest.TestCase):
	def test_draft(self):
		self.assertEqual(gov.available_actions(gov.DRAFT, [OFFICER]), ["calculate"])
		self.assertEqual(gov.available_actions(gov.DRAFT, [MANAGER]), ["calculate", "cancel"])

	def test_calculated(self):
		self.assertEqual(gov.available_actions(gov.CALCULATED, [OFFICER]),
						 ["calculate", "submit_for_review"])
		self.assertEqual(gov.available_actions(gov.CALCULATED, [MANAGER]),
						 ["calculate", "submit_for_review", "cancel"])

	def test_under_review(self):
		# Officer prepares only — cannot approve or cancel.
		self.assertEqual(gov.available_actions(gov.UNDER_REVIEW, [OFFICER]), ["calculate"])
		self.assertEqual(gov.available_actions(gov.UNDER_REVIEW, [MANAGER]),
						 ["calculate", "approve", "cancel"])

	def test_approved(self):
		self.assertEqual(gov.available_actions(gov.APPROVED, [OFFICER]), [])
		self.assertEqual(gov.available_actions(gov.APPROVED, [MANAGER]), ["submit", "cancel"])

	def test_submitted_lock_is_admin_only(self):
		self.assertEqual(gov.available_actions(gov.SUBMITTED, [MANAGER]), [])
		self.assertEqual(gov.available_actions(gov.SUBMITTED, [ADMIN]), ["lock"])

	def test_locked_unlock_is_admin_only(self):
		self.assertEqual(gov.available_actions(gov.LOCKED, [MANAGER]), [])
		self.assertEqual(gov.available_actions(gov.LOCKED, [ADMIN]), ["unlock"])

	def test_cancelled_is_terminal(self):
		for roles in ([OFFICER], [MANAGER], [ADMIN], [SYSMGR]):
			self.assertEqual(gov.available_actions(gov.CANCELLED, roles), [])

	def test_system_manager_sees_all_state_valid(self):
		# SYSMGR bypasses the role matrix, so it sees every action valid FROM state.
		self.assertEqual(gov.available_actions(gov.UNDER_REVIEW, [SYSMGR]),
						 ["calculate", "approve", "cancel"])
		self.assertEqual(gov.available_actions(gov.SUBMITTED, [SYSMGR]), ["lock"])

	def test_no_role_sees_nothing(self):
		self.assertEqual(gov.available_actions(gov.CALCULATED, []), [])

	def test_none_state_defaults_to_draft(self):
		self.assertEqual(gov.available_actions(None, [OFFICER]), ["calculate"])


# --------------------------- API dispatch (fake frappe) --------------------------- #
def _raise(msg):
	raise RuntimeError(msg)


class FakeRun:
	def __init__(self, state=gov.UNDER_REVIEW):
		self.name = "RUN-1"
		self.workflow_state = state
		self.run_status = "Completed With Warnings"
		self.error_count = 0
		self.calculated_by = "officer@x"
		self.approved_by = "mgr@x"
		self.calls = []

	def get(self, field):
		return getattr(self, field, None)

	# governance methods (mimic the controller: record call + transition)
	def calculate_run(self):
		self.calls.append("calculate_run"); self.workflow_state = gov.CALCULATED
	def submit_for_review(self):
		self.calls.append("submit_for_review"); self.workflow_state = gov.UNDER_REVIEW
	def approve_run(self):
		self.calls.append("approve_run"); self.workflow_state = gov.APPROVED
	def submit_run(self):
		self.calls.append("submit_run"); self.workflow_state = gov.SUBMITTED
	def cancel_run(self):
		self.calls.append("cancel_run"); self.workflow_state = gov.CANCELLED
	def lock_run(self):
		self.calls.append("lock_run"); self.workflow_state = gov.LOCKED
	def unlock_run(self):
		self.calls.append("unlock_run"); self.workflow_state = gov.SUBMITTED


class TestApiDispatch(unittest.TestCase):
	def _load_api(self, roles, run_doc, events=None):
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.session = types.SimpleNamespace(user="actor@x")
		frappe.get_roles = lambda *a, **k: list(roles)
		frappe.get_doc = lambda dt, name=None: run_doc
		frappe.get_all = lambda *a, **k: list(events or [])

		def whitelist(*a, **k):
			def deco(f):
				return f
			return deco if not (a and callable(a[0])) else a[0]
		frappe.whitelist = whitelist
		sys.modules["frappe"] = frappe
		import importlib
		mod = importlib.import_module("iraqi_government_payroll.api.payroll_api")
		importlib.reload(mod)
		return mod

	def test_action_dispatches_to_controller_method(self):
		doc = FakeRun(gov.UNDER_REVIEW)
		api = self._load_api([ADMIN], doc)
		res = api.run_governance_action("RUN-1", "approve")
		self.assertEqual(doc.calls, ["approve_run"])           # routed to the right method
		self.assertEqual(res["workflow_state"], gov.APPROVED)
		# allowed_actions reflects the NEW state + caller roles (Admin from Approved)
		self.assertEqual(res["allowed_actions"], ["submit", "cancel"])
		self.assertEqual(res["name"], "RUN-1")

	def test_lock_routes_to_lock_run(self):
		doc = FakeRun(gov.SUBMITTED)
		api = self._load_api([ADMIN], doc)
		res = api.run_governance_action("RUN-1", "lock")
		self.assertEqual(doc.calls, ["lock_run"])
		self.assertEqual(res["workflow_state"], gov.LOCKED)
		self.assertEqual(res["allowed_actions"], ["unlock"])

	def test_unknown_action_rejected_before_dispatch(self):
		doc = FakeRun()
		api = self._load_api([ADMIN], doc)
		with self.assertRaises(Exception):
			api.run_governance_action("RUN-1", "nuke")
		self.assertEqual(doc.calls, [])                        # nothing invoked

	def test_get_run_governance_shape(self):
		doc = FakeRun(gov.UNDER_REVIEW)
		events = [{"action": "calculate", "from_state": "Draft", "to_state": "Calculated",
				   "actor": "officer@x", "event_timestamp": "2026-01-01 00:00:00"}]
		api = self._load_api([MANAGER], doc, events=events)
		res = api.get_run_governance("RUN-1")
		self.assertEqual(res["workflow_state"], gov.UNDER_REVIEW)
		self.assertEqual(res["allowed_actions"], ["calculate", "approve", "cancel"])  # Manager
		self.assertEqual(res["events"], events)
		self.assertEqual(res["audit"]["approved_by"], "mgr@x")
		self.assertIn("locked_by", res["audit"])
		self.assertEqual(res["run_status"], "Completed With Warnings")


class TestCreatePayrollRun(unittest.TestCase):
	"""create_payroll_run validation + duplicate guard (fake frappe)."""

	def _load(self, *, existing=None, dup_rows=None, roles=None):
		existing = set(existing or ())          # {(doctype, name), ...}
		captured = {}
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.session = types.SimpleNamespace(user="officer@x")
		frappe.get_roles = lambda *a, **k: list(roles or [ADMIN])
		frappe.db = types.SimpleNamespace(
			exists=lambda dt, name=None: (dt, name) in existing)

		def get_all(dt, filters=None, fields=None, **k):
			captured["filters"] = filters
			return list(dup_rows or [])
		frappe.get_all = get_all

		class NewRun:
			def __init__(self, payload):
				self.payload = payload
				self.name = "PR-NEW"
				self.workflow_state = "Draft"

			def insert(self):
				return self
		frappe.get_doc = lambda payload: NewRun(payload)

		def whitelist(*a, **k):
			def deco(f):
				return f
			return deco if not (a and callable(a[0])) else a[0]
		frappe.whitelist = whitelist
		sys.modules["frappe"] = frappe
		import importlib
		mod = importlib.import_module("iraqi_government_payroll.api.payroll_api")
		importlib.reload(mod)
		return mod, captured

	def test_happy_path_all_scope(self):
		api, cap = self._load(existing={("Payroll Period", "P1"),
										 ("Government Rule Set", "IRAQ-2015")})
		res = api.create_payroll_run("P1", "IRAQ-2015", "All", None)
		self.assertEqual(res["name"], "PR-NEW")
		self.assertEqual(res["workflow_state"], "Draft")
		self.assertEqual(res["allowed_actions"], ["calculate", "cancel"])  # Admin from Draft
		# duplicate guard excludes Cancelled runs
		self.assertEqual(cap["filters"]["workflow_state"], ["!=", gov.CANCELLED])

	def test_missing_period_rejected(self):
		api, _ = self._load(existing=set())
		with self.assertRaises(Exception):
			api.create_payroll_run("NOPE", None, "All", None)

	def test_invalid_scope_rejected(self):
		api, _ = self._load(existing={("Payroll Period", "P1")})
		with self.assertRaises(Exception):
			api.create_payroll_run("P1", None, "Galaxy", None)

	def test_unknown_rule_set_rejected(self):
		api, _ = self._load(existing={("Payroll Period", "P1")})
		with self.assertRaises(Exception):
			api.create_payroll_run("P1", "NO-RULES", "All", None)

	def test_employee_scope_requires_reference(self):
		api, _ = self._load(existing={("Payroll Period", "P1")})
		with self.assertRaises(Exception):
			api.create_payroll_run("P1", None, "Employee", None)

	def test_employee_scope_reference_must_exist(self):
		api, _ = self._load(existing={("Payroll Period", "P1")})
		with self.assertRaises(Exception):
			api.create_payroll_run("P1", None, "Employee", "GHOST")

	def test_employee_scope_happy(self):
		api, _ = self._load(existing={
			("Payroll Period", "P1"),
			("Government Employee Payroll Profile", "EMP1")})
		res = api.create_payroll_run("P1", None, "Employee", "EMP1")
		self.assertEqual(res["workflow_state"], "Draft")

	def test_duplicate_active_run_rejected(self):
		api, _ = self._load(
			existing={("Payroll Period", "P1"), ("Government Rule Set", "IRAQ-2015")},
			dup_rows=[{"name": "PR-1", "rule_set": "IRAQ-2015", "scope_reference": None}])
		with self.assertRaises(Exception):
			api.create_payroll_run("P1", "IRAQ-2015", "All", None)

	def test_different_rule_set_not_a_duplicate(self):
		api, _ = self._load(
			existing={("Payroll Period", "P1"), ("Government Rule Set", "IRAQ-2015"),
					  ("Government Rule Set", "IRAQ-2008")},
			dup_rows=[{"name": "PR-1", "rule_set": "IRAQ-2008", "scope_reference": None}])
		res = api.create_payroll_run("P1", "IRAQ-2015", "All", None)  # different rule_set
		self.assertEqual(res["workflow_state"], "Draft")


class TestCurrentUser(unittest.TestCase):
	def test_returns_user_and_roles(self):
		frappe = types.ModuleType("frappe")
		frappe.session = types.SimpleNamespace(user="someone@example.com")
		frappe.get_roles = lambda u: ["Read Only User", "Auditor"]

		def whitelist(*a, **k):
			def deco(f):
				return f
			return deco if not (a and callable(a[0])) else a[0]
		frappe.whitelist = whitelist
		sys.modules["frappe"] = frappe
		import importlib
		mod = importlib.import_module("iraqi_government_payroll.api.payroll_api")
		importlib.reload(mod)
		res = mod.current_user()
		self.assertEqual(res["user"], "someone@example.com")
		self.assertEqual(res["roles"], ["Read Only User", "Auditor"])


if __name__ == "__main__":
	unittest.main()
