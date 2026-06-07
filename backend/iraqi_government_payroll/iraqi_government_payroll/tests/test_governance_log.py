# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 3 M5 immutable governance event log (pure + fake-frappe, no bench).

Run:  python3 -m unittest test_governance_log -v
"""

import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine import governance as gov  # noqa: E402

ADMIN = gov.PAYROLL_ADMINISTRATOR
MANAGER = gov.PAYROLL_MANAGER
OFFICER = gov.PAYROLL_OFFICER


# --------------------------- Pure event builder --------------------------- #
class TestBuildEvent(unittest.TestCase):
	def test_payload_fields(self):
		ev = gov.build_event("approve", gov.UNDER_REVIEW, gov.APPROVED,
							  "mgr@example.com", "2026-01-01 09:00:00", note="ok")
		self.assertEqual(ev["doctype"], "Payroll Run Governance Event")
		self.assertEqual(ev["action"], "approve")
		self.assertEqual(ev["from_state"], gov.UNDER_REVIEW)
		self.assertEqual(ev["to_state"], gov.APPROVED)
		self.assertEqual(ev["actor"], "mgr@example.com")
		self.assertEqual(ev["event_timestamp"], "2026-01-01 09:00:00")
		self.assertEqual(ev["note"], "ok")

	def test_none_from_state_defaults_to_draft(self):
		ev = gov.build_event("calculate", None, gov.CALCULATED, "u", "t")
		self.assertEqual(ev["from_state"], gov.DRAFT)
		self.assertEqual(ev["note"], "")


# --------------------------- Controller append + immutability --------------------------- #
def _raise(msg):
	raise RuntimeError(msg)


class TestGovernanceLogController(unittest.TestCase):
	"""Exercise the real Payroll Run controller; capture inserted governance events."""

	def _load(self, roles, fail_insert=False):
		captured = []
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.session = types.SimpleNamespace(user="actor@example.com")
		frappe.utils = types.SimpleNamespace(now=lambda: "2026-01-01 00:00:00")
		frappe.get_roles = lambda *a, **k: list(roles)

		class _Event:
			def __init__(self, payload):
				self.payload = payload

			def insert(self, *a, **k):
				if fail_insert:
					raise RuntimeError("db write failed")
				captured.append(self.payload)
				return self

		frappe.get_doc = lambda payload: _Event(payload)

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
		return mod.PayrollRun, captured

	def _new(self, cls, **attrs):
		inst = cls()
		inst.name = "RUN-001"
		inst.error_count = 0
		for k, v in attrs.items():
			setattr(inst, k, v)
		return inst

	def test_each_transition_appends_one_event(self):
		cls, events = self._load([ADMIN])
		inst = self._new(cls, workflow_state=gov.UNDER_REVIEW)
		inst.approve_run()
		self.assertEqual(len(events), 1)
		ev = events[0]
		self.assertEqual(ev["action"], "approve")
		self.assertEqual(ev["from_state"], gov.UNDER_REVIEW)
		self.assertEqual(ev["to_state"], gov.APPROVED)
		self.assertEqual(ev["actor"], "actor@example.com")
		self.assertEqual(ev["payroll_run"], "RUN-001")

	def test_full_lifecycle_including_unlock_resubmit_is_ordered(self):
		cls, events = self._load([ADMIN])
		inst = self._new(cls, workflow_state=gov.CALCULATED)
		inst.submit_for_review()      # Calculated -> Under Review
		inst.approve_run()            # Under Review -> Approved
		inst.submit_run()             # Approved -> Submitted
		inst.lock_run()               # Submitted -> Locked
		inst.unlock_run()             # Locked -> Submitted
		inst.lock_run()               # Submitted -> Locked (again)
		actions = [(e["action"], e["from_state"], e["to_state"]) for e in events]
		self.assertEqual(actions, [
			("submit_for_review", gov.CALCULATED, gov.UNDER_REVIEW),
			("approve", gov.UNDER_REVIEW, gov.APPROVED),
			("submit", gov.APPROVED, gov.SUBMITTED),
			("lock", gov.SUBMITTED, gov.LOCKED),
			("unlock", gov.LOCKED, gov.SUBMITTED),
			("lock", gov.SUBMITTED, gov.LOCKED),
		])

	def test_failed_event_insert_aborts_transition(self):
		cls, events = self._load([ADMIN], fail_insert=True)
		inst = self._new(cls, workflow_state=gov.UNDER_REVIEW)
		with self.assertRaises(Exception):
			inst.approve_run()
		self.assertEqual(events, [])    # nothing logged

	def test_cancel_is_logged(self):
		cls, events = self._load([MANAGER])
		inst = self._new(cls, workflow_state=gov.CALCULATED)
		inst.cancel_run()
		self.assertEqual(len(events), 1)
		self.assertEqual(events[0]["action"], "cancel")
		self.assertEqual(events[0]["to_state"], gov.CANCELLED)


# --------------------------- Immutability guard --------------------------- #
class TestGovernanceEventImmutable(unittest.TestCase):
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
			"payroll_run_governance_event.payroll_run_governance_event")
		importlib.reload(mod)
		return mod.PayrollRunGovernanceEvent

	def test_update_blocked_when_already_saved(self):
		cls = self._load_controller()
		inst = cls()
		inst.on_update()                       # brand-new -> allowed
		inst.get_doc_before_save = lambda: object()
		with self.assertRaises(Exception):     # persisted -> blocked
			inst.on_update()

	def test_delete_always_blocked(self):
		cls = self._load_controller()
		inst = cls()
		with self.assertRaises(Exception):
			inst.on_trash()


if __name__ == "__main__":
	unittest.main()
