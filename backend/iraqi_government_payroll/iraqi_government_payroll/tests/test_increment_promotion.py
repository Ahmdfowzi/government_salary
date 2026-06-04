# Copyright (c) 2026, Iraqi Government Payroll
"""Unit tests for the M6 Annual Increment + Promotion engines (pure, no bench).

Run:  python3 -m unittest test_increment_promotion -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.increment.increment_service import compute_increment  # noqa: E402
from iraqi_government_payroll.services.promotion.promotion_service import (  # noqa: E402
	compute_promotion, place_stage,
)
from iraqi_government_payroll.services.payroll_engine.types import PayrollError  # noqa: E402
from iraqi_government_payroll.services.audit.audit_service import (  # noqa: E402
	build_increment_snapshot_payload, build_promotion_snapshot_payload,
)


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


SCALE = fx("government_salary_scale.json")[0]["details"]
PROMOTION_RULE = fx("promotion_rule.json")[0]
INCREMENT_RULE = fx("annual_increment_rule.json")[0]
EFF = "2020-06-01"


# --------------------------- Annual Increment --------------------------- #
class TestAnnualIncrement(unittest.TestCase):
	def test_eligible_stage1_to_stage2(self):
		p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2019-05-01"}
		r = compute_increment(p, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		self.assertTrue(r.applied)
		self.assertEqual(r.new_state["current_stage"], 2)
		self.assertEqual(r.new_state["grade_code"], "7")          # grade unchanged

	def test_not_eligible_before_12_months(self):
		p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2020-01-01"}
		r = compute_increment(p, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		self.assertFalse(r.applied)
		self.assertTrue(any("Not eligible" in w for w in r.warnings))

	def test_stage_11_max_stage_warning(self):
		p = {"grade_code": "7", "current_stage": 11, "current_stage_date": "2018-01-01"}
		r = compute_increment(p, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		self.assertFalse(r.applied)
		self.assertTrue(any("Max stage" in w and "promotion" in w.lower() for w in r.warnings))

	def test_current_stage_date_updated(self):
		p = {"grade_code": "7", "current_stage": 3, "current_stage_date": "2019-01-01"}
		r = compute_increment(p, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		self.assertEqual(r.new_state["current_stage_date"], EFF)

	def test_profile_mutation_payload(self):
		p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2019-01-01"}
		r = compute_increment(p, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		self.assertEqual(set(r.profile_mutation.keys()), {"current_stage", "current_stage_date"})
		self.assertEqual(r.profile_mutation["current_stage"], 2)

	def test_snapshot_payload(self):
		p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2019-01-01"}
		r = compute_increment(p, INCREMENT_RULE, EFF, rule_set="IRAQ-2015")
		s = build_increment_snapshot_payload(r, employee_profile="EMP-1", source_request="AIR-1")
		self.assertEqual(s["calculation_type"], "Annual Increment")
		self.assertEqual(s["rule_set"], "IRAQ-2015")
		self.assertEqual(s["period_date"], EFF)
		out = json.loads(s["output_snapshot"])
		self.assertIn("new_state", out)
		self.assertIn("old_state", out)


# --------------------------- Promotion --------------------------- #
class TestPromotion(unittest.TestCase):
	def test_eligible_grade7_to_grade6(self):
		p = {"grade_code": "7", "current_stage": 1, "current_grade_date": "2015-01-01"}
		r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")
		self.assertTrue(r.applied)
		self.assertEqual(r.to_grade, "6")
		self.assertEqual(r.old_salary, 296000)
		self.assertEqual(r.new_stage, 1)               # 296000 < grade6 first stage 362000
		self.assertEqual(r.new_salary, 362000)

	def test_not_eligible_before_duration(self):
		p = {"grade_code": "7", "current_stage": 1, "current_grade_date": "2018-06-01"}  # 2y < 4y
		r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")
		self.assertFalse(r.applied)
		self.assertTrue(any("Not eligible" in w for w in r.warnings))

	def test_stage_placement_equal(self):
		rows = [{"stage": 1, "basic_salary": 500000}, {"stage": 2, "basic_salary": 600000}]
		self.assertEqual(place_stage(rows, 600000), 2)

	def test_stage_placement_between_next_higher(self):
		rows = [{"stage": 1, "basic_salary": 500000}, {"stage": 2, "basic_salary": 600000}]
		self.assertEqual(place_stage(rows, 550000), 2)

	def test_stage_placement_below_first(self):
		rows = [{"stage": 1, "basic_salary": 500000}, {"stage": 2, "basic_salary": 600000}]
		self.assertEqual(place_stage(rows, 400000), 1)

	def test_no_duration_rule_raises(self):
		p = {"grade_code": "1", "current_stage": 1, "current_grade_date": "2010-01-01"}
		with self.assertRaises(PayrollError):
			compute_promotion(p, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")

	def test_senior_grade_does_not_auto_promote(self):
		p = {"grade_code": "SPECIAL_A", "current_stage": 1, "current_grade_date": "2010-01-01"}
		r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")
		self.assertFalse(r.applied)
		self.assertTrue(any("Senior grade" in w for w in r.warnings))

	def test_profile_mutation_payload(self):
		p = {"grade_code": "7", "current_stage": 1, "current_grade_date": "2015-01-01"}
		r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")
		self.assertEqual(set(r.profile_mutation.keys()),
						 {"grade_code", "current_grade", "current_stage",
						  "current_grade_date", "current_stage_date"})
		self.assertEqual(r.profile_mutation["grade_code"], "6")
		self.assertEqual(r.profile_mutation["current_grade"], 6)

	def test_snapshot_payload(self):
		p = {"grade_code": "7", "current_stage": 1, "current_grade_date": "2015-01-01"}
		r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF, rule_set="IRAQ-2015")
		s = build_promotion_snapshot_payload(r, employee_profile="EMP-1", source_request="PRM-1")
		self.assertEqual(s["calculation_type"], "Promotion")
		self.assertEqual(s["rule_set"], "IRAQ-2015")
		self.assertEqual(s["period_date"], EFF)
		out = json.loads(s["output_snapshot"])
		self.assertEqual(out["new_state"]["grade_code"], "6")


if __name__ == "__main__":
	unittest.main()
