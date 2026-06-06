# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 3 M2 employee lifecycle (pure, no bench).

Run:  python3 -m unittest test_lifecycle -v
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.lifecycle import lifecycle_service as lc  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.types import PayrollError  # noqa: E402


class TestLifecycleTransitions(unittest.TestCase):
	def test_appointment_flow(self):
		self.assertEqual(lc.next_status("appoint", None), lc.ACTIVE)

	def test_transfer_flow(self):
		self.assertEqual(lc.next_status("transfer", lc.ACTIVE), lc.ACTIVE)
		with self.assertRaises(PayrollError):
			lc.next_status("transfer", lc.RETIRED)

	def test_leave_flow(self):
		self.assertEqual(lc.next_status("start_leave", lc.ACTIVE), lc.ON_LEAVE)
		with self.assertRaises(PayrollError):
			lc.next_status("start_leave", lc.ON_LEAVE)

	def test_return_flow(self):
		self.assertEqual(lc.next_status("return", lc.ON_LEAVE), lc.ACTIVE)
		with self.assertRaises(PayrollError):
			lc.next_status("return", lc.ACTIVE)

	def test_retirement_flow(self):
		self.assertEqual(lc.next_status("retire", lc.ACTIVE), lc.RETIRED)
		self.assertEqual(lc.next_status("retire", lc.ON_LEAVE), lc.RETIRED)
		for terminal in (lc.RETIRED, lc.TERMINATED):
			with self.assertRaises(PayrollError):
				lc.next_status("retire", terminal)

	def test_termination_flow(self):
		self.assertEqual(lc.next_status("terminate", lc.ACTIVE), lc.TERMINATED)
		self.assertEqual(lc.next_status("terminate", lc.ON_LEAVE), lc.TERMINATED)
		with self.assertRaises(PayrollError):
			lc.next_status("terminate", lc.RETIRED)

	def test_unknown_event(self):
		with self.assertRaises(PayrollError):
			lc.next_status("promote", lc.ACTIVE)


class TestPayrollExclusion(unittest.TestCase):
	def test_is_payroll_eligible(self):
		self.assertTrue(lc.is_payroll_eligible(lc.ACTIVE))
		self.assertTrue(lc.is_payroll_eligible(None))            # default Active
		for s in (lc.ON_LEAVE, lc.RETIRED, lc.TERMINATED):
			self.assertFalse(lc.is_payroll_eligible(s))

	def test_filter_payroll_eligible(self):
		profiles = [
			{"name": "A", "employment_status": lc.ACTIVE},
			{"name": "B", "employment_status": lc.RETIRED},
			{"name": "C", "employment_status": lc.TERMINATED},
			{"name": "D", "employment_status": lc.ON_LEAVE},
			{"name": "E"},                                       # missing -> Active
		]
		eligible = [p["name"] for p in lc.filter_payroll_eligible(profiles)]
		self.assertEqual(eligible, ["A", "E"])


class TestTimelineReconstruction(unittest.TestCase):
	def setUp(self):
		self.events = [
			{"date": "2010-01-01", "event": "appoint", "entity": "MIN-A", "position": "POS-1"},
			{"date": "2015-06-01", "event": "transfer", "entity": "MIN-B", "position": "POS-2"},
			{"date": "2018-03-01", "event": "start_leave"},
			{"date": "2019-03-01", "event": "return"},
			{"date": "2020-12-31", "event": "retire"},
		]

	def test_status_before_any_event(self):
		st = lc.status_as_of(self.events, "2009-01-01")
		self.assertIsNone(st["employment_status"])

	def test_status_after_appointment(self):
		st = lc.status_as_of(self.events, "2012-01-01")
		self.assertEqual(st["employment_status"], lc.ACTIVE)
		self.assertEqual(st["current_entity"], "MIN-A")

	def test_status_after_transfer(self):
		st = lc.status_as_of(self.events, "2016-01-01")
		self.assertEqual(st["employment_status"], lc.ACTIVE)
		self.assertEqual(st["current_entity"], "MIN-B")
		self.assertEqual(st["current_position"], "POS-2")

	def test_status_during_leave(self):
		st = lc.status_as_of(self.events, "2018-06-01")
		self.assertEqual(st["employment_status"], lc.ON_LEAVE)
		self.assertEqual(st["current_entity"], "MIN-B")        # entity preserved during leave

	def test_status_after_return(self):
		st = lc.status_as_of(self.events, "2019-06-01")
		self.assertEqual(st["employment_status"], lc.ACTIVE)

	def test_status_after_retirement(self):
		st = lc.status_as_of(self.events, "2021-01-01")
		self.assertEqual(st["employment_status"], lc.RETIRED)
		self.assertEqual(st["last_event"], "Retirement")


if __name__ == "__main__":
	unittest.main()
