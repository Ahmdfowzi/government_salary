# Copyright (c) 2026, Iraqi Government Payroll
"""M8 hardening / idempotency smoke tests (pure, no bench).

Run:  python3 -m unittest test_hardening -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.audit.audit_service import snapshot_is_duplicate  # noqa: E402
from iraqi_government_payroll.services.increment.increment_service import compute_increment  # noqa: E402
from iraqi_government_payroll.services.promotion.promotion_service import compute_promotion  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.engine import DataContext  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.payroll_run import run_payroll_batch  # noqa: E402


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


SCALE = fx("government_salary_scale.json")[0]["details"]
PROMOTION_RULE = fx("promotion_rule.json")[0]
INCREMENT_RULE = fx("annual_increment_rule.json")[0]
EFF = "2020-06-01"


class TestSnapshotDedup(unittest.TestCase):
	def test_salary_slip_snapshot_only_once(self):
		existing = [{"calculation_type": "Salary Slip", "salary_slip": "SAL-1"}]
		self.assertTrue(snapshot_is_duplicate(existing, calculation_type="Salary Slip", salary_slip="SAL-1"))
		self.assertFalse(snapshot_is_duplicate(existing, calculation_type="Salary Slip", salary_slip="SAL-2"))

	def test_request_snapshot_dedup(self):
		existing = [{"calculation_type": "Annual Increment", "source_request": "AIR-1"}]
		self.assertTrue(snapshot_is_duplicate(existing, calculation_type="Annual Increment", source_request="AIR-1"))
		self.assertFalse(snapshot_is_duplicate(existing, calculation_type="Annual Increment", source_request="AIR-2"))
		# different calculation_type must not match
		self.assertFalse(snapshot_is_duplicate(existing, calculation_type="Promotion", source_request="AIR-1"))


class TestIncrementNotDoubleApplied(unittest.TestCase):
	def test_reapply_on_mutated_profile_is_noop(self):
		p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2019-01-01"}
		r1 = compute_increment(p, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		self.assertTrue(r1.applied)
		self.assertEqual(r1.new_state["current_stage"], 2)
		# Feeding the mutated profile back in (stage date now EFF) must not increment again.
		r2 = compute_increment(r1.new_state, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		self.assertFalse(r2.applied)


class TestPromotionNotDoubleApplied(unittest.TestCase):
	def test_reapply_on_mutated_profile_is_noop(self):
		p = {"grade_code": "7", "current_stage": 1, "current_grade_date": "2015-01-01"}
		r1 = compute_promotion(p, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")
		self.assertTrue(r1.applied)
		self.assertEqual(r1.to_grade, "6")
		# Mutated profile (grade now 6, grade date EFF) is not yet eligible again.
		r2 = compute_promotion(r1.new_state, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")
		self.assertFalse(r2.applied)


class FakeSlipStore:
	def __init__(self):
		self.slips = {}

	def upsert(self, period, run, employee, rule_set, result):
		key = (period, employee)
		created = key not in self.slips
		self.slips[key] = {"net_salary": result.net_salary}
		return f"SAL-{employee}", created


class TestPayrollRunIdempotency(unittest.TestCase):
	def test_rerun_does_not_duplicate(self):
		ctx = DataContext(fx("government_rule_set.json"), fx("government_salary_scale.json"),
						  fx("allowance_rule.json"), fx("income_tax_bracket.json"),
						  fx("tax_allowance_rule.json"))
		profiles = [{"name": "EMP-1", "grade_code": "7", "current_stage": 1, "qualification": "Bachelor"}]
		store = FakeSlipStore()
		run_payroll_batch("PP-2020-6", "PR-1", "IRAQ-2015", profiles, ctx, store, EFF)
		r2 = run_payroll_batch("PP-2020-6", "PR-1", "IRAQ-2015", profiles, ctx, store, EFF)
		self.assertEqual(len(store.slips), 1)
		self.assertFalse(r2.outcomes[0].created)


if __name__ == "__main__":
	unittest.main()
