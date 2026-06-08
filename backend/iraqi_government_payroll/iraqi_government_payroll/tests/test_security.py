# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 5 M1 security / roles / sensitive-action access control.

Run:  python3 -m unittest test_security -v
"""

import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.security import access  # noqa: E402
from iraqi_government_payroll.services.payroll_engine import governance as gov  # noqa: E402

GOV_ADMIN = access.GOVERNMENT_PAYROLL_ADMINISTRATOR
ADMIN = access.PAYROLL_ADMINISTRATOR
MANAGER = access.PAYROLL_MANAGER
OFFICER = access.PAYROLL_OFFICER
FINANCE = access.FINANCE_OFFICER
HR = access.HR_OFFICER
AUDITOR = access.AUDITOR
READONLY = access.READ_ONLY_USER
SYSMGR = access.SYSTEM_MANAGER


# --------------------------- Pure sensitive-action matrix --------------------------- #
class TestAccessMatrix(unittest.TestCase):
	def test_increment_promotion_approval(self):
		for action in ("approve_increment", "approve_promotion"):
			for role in (MANAGER, ADMIN, GOV_ADMIN, SYSMGR):
				self.assertTrue(access.is_allowed(action, [role]), (action, role))
			for role in (OFFICER, HR, FINANCE, AUDITOR, READONLY):
				self.assertFalse(access.is_allowed(action, [role]), (action, role))

	def test_accounting_export(self):
		for role in (FINANCE, access.FINANCE_USER, MANAGER, ADMIN, GOV_ADMIN, SYSMGR):
			self.assertTrue(access.is_allowed("export_accounting_journal", [role]), role)
		for role in (AUDITOR, READONLY, HR, OFFICER):
			self.assertFalse(access.is_allowed("export_accounting_journal", [role]), role)

	def test_superusers_and_failclosed(self):
		self.assertTrue(access.is_allowed("approve_increment", [GOV_ADMIN]))
		self.assertTrue(access.is_allowed("approve_increment", [SYSMGR]))
		self.assertFalse(access.is_allowed("nuke", [GOV_ADMIN, SYSMGR]))   # unknown -> closed
		self.assertFalse(access.is_allowed("approve_increment", []))

	def test_ensure_allowed_raises(self):
		with self.assertRaises(access.AccessDenied):
			access.ensure_allowed("export_accounting_journal", [READONLY])
		self.assertTrue(access.ensure_allowed("export_accounting_journal", [FINANCE]))
		with self.assertRaises(access.AccessDenied):
			access.ensure_allowed("nuke", [SYSMGR])


# --------------------------- Governance admits Government Payroll Administrator --------------------------- #
class TestGovernanceSuperuser(unittest.TestCase):
	def test_gov_admin_can_lock_unlock_like_system_manager(self):
		for action in gov.REQUIRED_ROLES:
			self.assertTrue(gov.role_allowed(action, [GOV_ADMIN]), action)
		# explicit: lock/unlock (Administrator-only actions) now admit the new role
		self.assertTrue(gov.role_allowed("lock", [GOV_ADMIN]))
		self.assertTrue(gov.role_allowed("unlock", [GOV_ADMIN]))

	def test_existing_role_matrix_unchanged(self):
		# Officer still cannot approve; Manager cannot lock (M4 behaviour intact)
		self.assertFalse(gov.role_allowed("approve", [OFFICER]))
		self.assertFalse(gov.role_allowed("lock", [MANAGER]))
		self.assertTrue(gov.role_allowed("lock", [ADMIN]))


# --------------------------- Endpoint / controller wiring (fake frappe) --------------------------- #
def _raise(msg):
	raise RuntimeError(msg)


class TestAccountingExportGate(unittest.TestCase):
	"""accounting_api.journal_export is gated by the export role."""

	def _load(self, roles):
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.response = {}
		frappe.session = types.SimpleNamespace(user="u")
		frappe.get_roles = lambda *a, **k: list(roles)
		frappe.db = types.SimpleNamespace(get_value=lambda dt, name, field: "Calculated")
		frappe.get_single = lambda dt: types.SimpleNamespace(get=lambda f: "ACC")

		def get_all(dt, filters=None, fields=None, **k):
			if dt == "Salary Slip" and fields and "basic_salary" in fields:
				return [{"name": "S1", "employee_profile": "E1", "employee_name": "A",
						 "grade_code": "7", "stage": 1, "basic_salary": 100, "total_earnings": 100,
						 "total_deductions": 0, "net_salary": 100}]
			return []
		frappe.get_all = get_all

		def whitelist(*a, **k):
			def deco(f):
				return f
			return deco if not (a and callable(a[0])) else a[0]
		frappe.whitelist = whitelist
		sys.modules["frappe"] = frappe
		import importlib
		from iraqi_government_payroll.api import reports_api
		importlib.reload(reports_api)
		from iraqi_government_payroll.api import accounting_api
		importlib.reload(accounting_api)
		return accounting_api

	def test_finance_officer_can_export(self):
		api = self._load([FINANCE])
		res = api.journal_export("RUN-1")
		self.assertTrue(res["balanced"])

	def test_read_only_user_denied(self):
		api = self._load([READONLY])
		with self.assertRaises(Exception):
			api.journal_export("RUN-1")

	def test_auditor_denied(self):
		api = self._load([AUDITOR])
		with self.assertRaises(Exception):
			api.export_journal("RUN-1")


class TestIncrementPromotionApprovalGate(unittest.TestCase):
	"""Increment/Promotion on_submit is gated by the approval role."""

	def _load_controller(self, module_path, cls_name, roles):
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.session = types.SimpleNamespace(user="u")
		frappe.get_roles = lambda *a, **k: list(roles)
		model = types.ModuleType("frappe.model")
		document = types.ModuleType("frappe.model.document")

		class _Doc:
			pass
		document.Document = _Doc
		model.document = document
		frappe.model = model
		sys.modules["frappe"] = frappe
		sys.modules["frappe.model"] = model
		sys.modules["frappe.model.document"] = document
		import importlib
		mod = importlib.import_module(module_path)
		importlib.reload(mod)
		return getattr(mod, cls_name)

	def test_increment_denied_for_officer(self):
		cls = self._load_controller(
			"iraqi_government_payroll.government_payroll.doctype."
			"annual_increment_request.annual_increment_request",
			"AnnualIncrementRequest", [OFFICER])
		with self.assertRaises(Exception):
			cls().on_submit()                       # denied before repository.apply_increment

	def test_promotion_denied_for_readonly(self):
		cls = self._load_controller(
			"iraqi_government_payroll.government_payroll.doctype."
			"promotion_request.promotion_request",
			"PromotionRequest", [READONLY])
		with self.assertRaises(Exception):
			cls().on_submit()


if __name__ == "__main__":
	unittest.main()
