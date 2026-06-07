# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 3 M3 payroll locking & historical integrity (pure, no bench).

Run:  python3 -m unittest test_locking -v
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
from iraqi_government_payroll.services.historical import history_service as hist  # noqa: E402


# --------------------------- Locking state machine --------------------------- #
class TestLockingTransitions(unittest.TestCase):
	def test_lock_submitted_run(self):
		self.assertEqual(gov.ensure_can_lock(gov.SUBMITTED), gov.LOCKED)

	def test_lock_only_from_submitted(self):
		for state in (gov.DRAFT, gov.CALCULATED, gov.UNDER_REVIEW, gov.APPROVED, gov.LOCKED, gov.CANCELLED):
			with self.assertRaises(PayrollError):
				gov.ensure_can_lock(state)

	def test_unlock_only_from_locked(self):
		self.assertEqual(gov.ensure_can_unlock(gov.LOCKED), gov.SUBMITTED)
		with self.assertRaises(PayrollError):
			gov.ensure_can_unlock(gov.SUBMITTED)

	def test_recalc_blocked_after_lock(self):
		with self.assertRaises(PayrollError):
			gov.ensure_can_calculate(gov.LOCKED)

	def test_delete_blocked_after_lock(self):
		with self.assertRaises(PayrollError):
			gov.ensure_can_delete(gov.LOCKED)

	def test_cancel_blocked_after_lock(self):
		with self.assertRaises(PayrollError):
			gov.next_state("cancel", gov.LOCKED)

	def test_is_locked(self):
		self.assertTrue(gov.is_locked(gov.LOCKED))
		self.assertFalse(gov.is_locked(gov.SUBMITTED))


# --------------------------- Retroactive protection --------------------------- #
class TestRetroactiveProtection(unittest.TestCase):
	def test_retroactive_into_locked_period_blocked(self):
		ends = ["2026-01-31"]
		self.assertTrue(hist.is_retroactive_to_locked("2026-01-15", ends))   # inside
		self.assertTrue(hist.is_retroactive_to_locked("2026-01-31", ends))   # boundary
		self.assertTrue(hist.is_retroactive_to_locked("2025-12-01", ends))   # before

	def test_future_change_allowed(self):
		self.assertFalse(hist.is_retroactive_to_locked("2026-02-01", ["2026-01-31"]))

	def test_no_locked_periods_allows_everything(self):
		self.assertFalse(hist.is_retroactive_to_locked("2020-01-01", []))


# --------------------------- Historical reconstruction --------------------------- #
class TestHistoricalReconstruction(unittest.TestCase):
	def setUp(self):
		self.snapshots = [
			{"period_date": "2026-01-01", "net_amount": 371487, "gross_amount": 429200,
			 "total_deductions": 57713, "grade_code": "7", "stage": 1, "rule_set": "IRAQ-2015"},
			{"period_date": "2026-02-01", "net_amount": 371487, "gross_amount": 429200,
			 "total_deductions": 57713, "grade_code": "7", "stage": 1, "rule_set": "IRAQ-2015"},
		]
		self.events = [
			{"date": "2010-01-01", "event": "appoint", "entity": "E1", "position": "P1"},
			{"date": "2026-03-01", "event": "transfer", "entity": "E2", "position": "P2"},
			{"date": "2026-06-01", "event": "retire"},
		]

	def test_latest_snapshot_on_or_before(self):
		self.assertEqual(hist.latest_snapshot_on_or_before(self.snapshots, "2026-01-15")["period_date"], "2026-01-01")
		self.assertEqual(hist.latest_snapshot_on_or_before(self.snapshots, "2026-03-01")["period_date"], "2026-02-01")
		self.assertIsNone(hist.latest_snapshot_on_or_before(self.snapshots, "2025-12-01"))

	def test_state_at_january_unaffected_by_later_changes(self):
		st = hist.reconstruct_state(self.snapshots, self.events, "2026-01-15")
		self.assertEqual(st["payroll"]["net_amount"], 371487)
		self.assertEqual(st["entity"], "E1")                 # entity as of January
		self.assertEqual(st["employment_status"], "Active")

	def test_later_promotion_transfer_retirement_do_not_change_history(self):
		# As of a later date the live state changed (E2 / Retired) but the
		# historical payroll snapshot value is still the January figure.
		later = hist.reconstruct_state(self.snapshots, self.events, "2026-07-01")
		self.assertEqual(later["entity"], "E2")
		self.assertEqual(later["employment_status"], "Retired")
		self.assertEqual(later["payroll"]["net_amount"], 371487)  # unchanged historical value
		# and January reconstruction is still identical
		jan = hist.reconstruct_state(self.snapshots, self.events, "2026-01-15")
		self.assertEqual(jan["payroll"]["net_amount"], 371487)
		self.assertEqual(jan["entity"], "E1")


def _raise(msg):
	raise RuntimeError(msg)


class TestPayrollRunDeleteGuard(unittest.TestCase):
	"""Exercise the real Payroll Run controller on_trash with a fake frappe."""

	def _load_controller(self):
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.session = types.SimpleNamespace(user="Administrator")
		frappe.utils = types.SimpleNamespace(now=lambda: "2026-01-01 00:00:00")
		frappe.get_roles = lambda *a, **k: ["System Manager"]

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

	def test_delete_blocked_for_locked_and_submitted(self):
		cls = self._load_controller()
		for state in ("Locked", "Submitted"):
			inst = cls()
			inst.workflow_state = state
			inst.docstatus = 0
			with self.assertRaises(Exception):
				inst.on_trash()

	def test_delete_blocked_for_submitted_docstatus(self):
		cls = self._load_controller()
		inst = cls()
		inst.workflow_state = "Approved"
		inst.docstatus = 1
		with self.assertRaises(Exception):
			inst.on_trash()

	def test_delete_allowed_for_draft(self):
		cls = self._load_controller()
		inst = cls()
		inst.workflow_state = "Draft"
		inst.docstatus = 0
		inst.on_trash()   # no raise

	def test_does_not_shadow_frappe_is_locked_property(self):
		# Regression: a method named `is_locked` on the controller shadows
		# frappe Document.is_locked (a property used by check_if_locked() on every
		# save), which broke all saves on a live bench. The lock-state helper must
		# be `is_run_locked`, and `is_locked` must NOT be defined on the class.
		cls = self._load_controller()
		self.assertNotIn("is_locked", vars(cls))
		self.assertTrue(callable(getattr(cls, "is_run_locked", None)))


if __name__ == "__main__":
	unittest.main()
