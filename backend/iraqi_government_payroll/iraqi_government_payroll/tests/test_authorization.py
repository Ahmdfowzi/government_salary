# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 3 M4 governance authorization / segregation of duties.

Pure role-matrix predicates plus the real Payroll Run controller exercised
against a fake frappe (no bench).

Run:  python3 -m unittest test_authorization -v
"""

import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine import governance as gov  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.types import PayrollError  # noqa: E402

OFFICER = gov.PAYROLL_OFFICER
MANAGER = gov.PAYROLL_MANAGER
ADMIN = gov.PAYROLL_ADMINISTRATOR
SYSMGR = gov.SYSTEM_MANAGER


# --------------------------- Pure role matrix --------------------------- #
class TestRoleMatrix(unittest.TestCase):
	def test_officer_may_prepare_only(self):
		for action in ("calculate", "submit_for_review"):
			self.assertTrue(gov.role_allowed(action, [OFFICER]))
		for action in ("approve", "submit", "cancel", "lock", "unlock"):
			self.assertFalse(gov.role_allowed(action, [OFFICER]))

	def test_manager_may_approve_submit_cancel_not_lock(self):
		for action in ("calculate", "submit_for_review", "approve", "submit", "cancel"):
			self.assertTrue(gov.role_allowed(action, [MANAGER]))
		for action in ("lock", "unlock"):
			self.assertFalse(gov.role_allowed(action, [MANAGER]))

	def test_administrator_may_do_everything(self):
		for action in gov.REQUIRED_ROLES:
			self.assertTrue(gov.role_allowed(action, [ADMIN]))

	def test_system_manager_bypasses_all(self):
		for action in gov.REQUIRED_ROLES:
			self.assertTrue(gov.role_allowed(action, [SYSMGR]))

	def test_no_role_denied_everywhere(self):
		for action in gov.REQUIRED_ROLES:
			self.assertFalse(gov.role_allowed(action, []))
			self.assertFalse(gov.role_allowed(action, ["HR User"]))

	def test_unknown_action_fails_closed(self):
		self.assertFalse(gov.role_allowed("nuke", [ADMIN, SYSMGR]))


class TestEnsureRoleAllowed(unittest.TestCase):
	def test_raises_when_unauthorized(self):
		with self.assertRaises(PayrollError):
			gov.ensure_role_allowed("approve", [OFFICER])

	def test_returns_true_when_authorized(self):
		self.assertTrue(gov.ensure_role_allowed("approve", [MANAGER]))

	def test_unknown_action_raises(self):
		with self.assertRaises(PayrollError):
			gov.ensure_role_allowed("nuke", [SYSMGR])


# --------------------------- Controller enforcement --------------------------- #
def _raise(msg):
	raise RuntimeError(msg)


class TestPayrollRunAuthorization(unittest.TestCase):
	"""Exercise the real Payroll Run controller transitions with a fake frappe."""

	def _load_controller(self, roles):
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.session = types.SimpleNamespace(user="someuser@example.com")
		frappe.utils = types.SimpleNamespace(now=lambda: "2026-01-01 00:00:00")
		frappe.get_roles = lambda *a, **k: list(roles)

		class _Event:
			def insert(self, *a, **k):
				return self

		frappe.get_doc = lambda payload: _Event()

		def whitelist(*a, **k):
			def deco(f):
				return f
			return deco if not (a and callable(a[0])) else a[0]
		frappe.whitelist = whitelist
		model = types.ModuleType("frappe.model")
		document = types.ModuleType("frappe.model.document")

		class _Doc:
			docstatus = 0

			def get_doc_before_save(self):
				return None

			def save(self):
				return None

		document.Document = _Doc
		model.document = document
		frappe.model = model
		sys.modules["frappe"] = frappe
		sys.modules["frappe.model"] = model
		sys.modules["frappe.model.document"] = document
		import importlib
		mod = importlib.import_module(
			"iraqi_government_payroll.government_payroll.doctype.payroll_run.payroll_run")
		importlib.reload(mod)
		return mod.PayrollRun

	def _run(self, roles, **attrs):
		cls = self._load_controller(roles)
		inst = cls()
		inst.name = "RUN-TEST"
		for k, v in attrs.items():
			setattr(inst, k, v)
		return inst

	def test_officer_cannot_approve(self):
		inst = self._run([OFFICER], workflow_state=gov.UNDER_REVIEW, error_count=0)
		with self.assertRaises(Exception):
			inst.approve_run()

	def test_manager_can_approve(self):
		inst = self._run([MANAGER], workflow_state=gov.UNDER_REVIEW, error_count=0)
		self.assertEqual(inst.approve_run(), gov.APPROVED)

	def test_officer_cannot_submit(self):
		inst = self._run([OFFICER], workflow_state=gov.APPROVED)
		with self.assertRaises(Exception):
			inst.submit_run()

	def test_manager_can_submit(self):
		inst = self._run([MANAGER], workflow_state=gov.APPROVED)
		self.assertEqual(inst.submit_run(), gov.SUBMITTED)

	def test_manager_cannot_lock(self):
		inst = self._run([MANAGER], workflow_state=gov.SUBMITTED)
		with self.assertRaises(Exception):
			inst.lock_run()

	def test_administrator_can_lock(self):
		inst = self._run([ADMIN], workflow_state=gov.SUBMITTED)
		self.assertEqual(inst.lock_run(), gov.LOCKED)

	def test_manager_cannot_unlock(self):
		inst = self._run([MANAGER], workflow_state=gov.LOCKED)
		with self.assertRaises(Exception):
			inst.unlock_run()

	def test_administrator_can_unlock(self):
		inst = self._run([ADMIN], workflow_state=gov.LOCKED)
		self.assertEqual(inst.unlock_run(), gov.SUBMITTED)

	def test_officer_can_submit_for_review(self):
		inst = self._run([OFFICER], workflow_state=gov.CALCULATED)
		self.assertEqual(inst.submit_for_review(), gov.UNDER_REVIEW)


if __name__ == "__main__":
	unittest.main()
