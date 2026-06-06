# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 3 M1 payroll-run governance (pure, no bench).

Run:  python3 -m unittest test_governance -v
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


class TestApprovalPath(unittest.TestCase):
	def test_normal_approval_path(self):
		s = gov.DRAFT
		s = gov.next_state("calculate", s)
		self.assertEqual(s, gov.CALCULATED)
		s = gov.next_state("submit_for_review", s)
		self.assertEqual(s, gov.UNDER_REVIEW)
		gov.ensure_can_approve(s, 0)            # no errors -> allowed
		s = gov.next_state("approve", s)
		self.assertEqual(s, gov.APPROVED)
		s = gov.next_state("submit", s)
		self.assertEqual(s, gov.SUBMITTED)

	def test_cancel_allowed_pre_submit(self):
		for state in (gov.DRAFT, gov.CALCULATED, gov.UNDER_REVIEW, gov.APPROVED):
			self.assertEqual(gov.next_state("cancel", state), gov.CANCELLED)

	def test_cancel_blocked_after_submit(self):
		with self.assertRaises(PayrollError):
			gov.next_state("cancel", gov.SUBMITTED)


class TestProtectionRules(unittest.TestCase):
	def test_recalculation_blocked_after_approval(self):
		for state in (gov.APPROVED, gov.SUBMITTED, gov.CANCELLED):
			with self.assertRaises(PayrollError):
				gov.ensure_can_calculate(state)
			with self.assertRaises(PayrollError):
				gov.next_state("calculate", state)

	def test_recalculation_allowed_before_approval(self):
		for state in (gov.DRAFT, gov.CALCULATED, gov.UNDER_REVIEW):
			self.assertEqual(gov.ensure_can_calculate(state), gov.CALCULATED)

	def test_approval_blocked_with_errors(self):
		with self.assertRaises(PayrollError):
			gov.ensure_can_approve(gov.UNDER_REVIEW, error_count=2)
		# zero errors is allowed
		self.assertEqual(gov.ensure_can_approve(gov.UNDER_REVIEW, error_count=0), gov.APPROVED)

	def test_approval_blocked_from_wrong_state(self):
		with self.assertRaises(PayrollError):
			gov.ensure_can_approve(gov.CALCULATED, error_count=0)

	def test_cannot_delete_submitted(self):
		with self.assertRaises(PayrollError):
			gov.ensure_can_delete(gov.SUBMITTED)
		for state in (gov.DRAFT, gov.CALCULATED, gov.UNDER_REVIEW, gov.APPROVED, gov.CANCELLED):
			self.assertTrue(gov.ensure_can_delete(state))


class TestSnapshotImmutability(unittest.TestCase):
	"""Exercise the real Payroll Calculation Snapshot controller with a fake frappe."""

	def _load_controller(self):
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		model = types.ModuleType("frappe.model")
		document = types.ModuleType("frappe.model.document")

		class _Doc:
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
			"iraqi_government_payroll.government_payroll.doctype."
			"payroll_calculation_snapshot.payroll_calculation_snapshot")
		importlib.reload(mod)
		return mod.PayrollCalculationSnapshot

	def test_update_blocked_when_already_saved(self):
		cls = self._load_controller()
		inst = cls()
		# brand-new doc (no prior version) -> allowed
		inst.on_update()
		# already-persisted doc -> blocked
		inst.get_doc_before_save = lambda: object()
		with self.assertRaises(Exception):
			inst.on_update()

	def test_delete_always_blocked(self):
		cls = self._load_controller()
		inst = cls()
		with self.assertRaises(Exception):
			inst.on_trash()


def _raise(msg):
	raise RuntimeError(msg)


if __name__ == "__main__":
	unittest.main()
