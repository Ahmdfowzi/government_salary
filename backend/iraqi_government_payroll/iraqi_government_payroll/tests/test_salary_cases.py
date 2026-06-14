# Copyright (c) 2026, Iraqi Government Payroll
"""Backend functional tests — Salary Calculation matrix (item 2).

Multiple grade/stage cases, married/children/missing-family, and the
missing-grade/stage and missing-rule-set error paths, all against the fixtures via
the real net-salary chain. Pure (no bench). Run:
    python3 -m unittest test_salary_cases -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine.engine import DataContext, EmployeeInput  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.net_salary import compute_net_salary  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.types import PayrollError  # noqa: E402
from iraqi_government_payroll.services.audit.audit_service import build_snapshot_payload  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.engine import calculate_active_salary  # noqa: E402


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


def ctx():
	return DataContext(
		rule_sets=fx("government_rule_set.json"),
		scales=fx("government_salary_scale.json"),
		allowance_rules=fx("allowance_rule.json"),
		income_tax_brackets=fx("income_tax_bracket.json"),
		tax_allowance_rules=fx("tax_allowance_rule.json"),
	)


def emp(grade, stage, **kw):
	base = dict(grade_code=grade, stage=stage, period_date="2020-06-01", qualification="Bachelor")
	base.update(kw)
	return EmployeeInput(**base)


# Expected basic salaries from the IRAQ-2015 scale (the grade/stage → basic link).
BASICS = {("1", 1): 910000, ("5", 5): 453000, ("7", 1): 296000,
		  ("10", 11): 200000, ("SPECIAL_A", 1): 2413000}


class TestGradeStageMatrix(unittest.TestCase):
	def _check(self, grade, stage):
		r = compute_net_salary(ctx(), emp(grade, stage))
		self.assertEqual(r.basic_salary, BASICS[(grade, stage)], f"{grade}/{stage} basic")
		# gross = basic + capped + non-capped allowances
		self.assertEqual(r.gross_salary,
						 r.basic_salary + r.capped_allowance_total + r.non_capped_allowance_total)
		# net = gross - (pension + tax + other), and deductions reconcile
		self.assertEqual(r.total_deductions, r.pension_deduction + r.tax + r.other_deductions)
		self.assertEqual(r.net_salary, r.gross_salary - r.total_deductions)
		self.assertGreater(r.net_salary, 0)
		return r

	def test_grade1_stage1(self):
		self._check("1", 1)

	def test_grade5_stage5(self):
		self._check("5", 5)

	def test_grade7_stage1(self):
		r = self._check("7", 1)
		self.assertEqual(r.gross_salary, 429200)         # 296000 + 45% Bachelor cert

	def test_grade10_stage11_max_stage(self):
		self._check("10", 11)

	def test_special_grade_a(self):
		r = self._check("SPECIAL_A", 1)
		self.assertEqual(r.basic_salary, 2413000)

	def test_200pct_cap_never_exceeded(self):
		# capped allowance total can never exceed 2x basic for any grade/stage
		for (g, s) in BASICS:
			r = compute_net_salary(ctx(), emp(g, s))
			self.assertLessEqual(r.capped_allowance_total, 2 * r.basic_salary, f"{g}/{s} cap")


class TestFamilyVariants(unittest.TestCase):
	def _codes(self, **kw):
		r = compute_net_salary(ctx(), emp("7", 1, **kw))
		return {l.component_code: l.amount for l in r.allowance_lines}, r

	def test_married_adds_spouse_allowance(self):
		codes, _ = self._codes(spouse_eligible=True)
		self.assertEqual(codes["FAM_SPOUSE"], 50000)

	def test_children_add_child_allowance(self):
		codes, _ = self._codes(children_count=3)
		self.assertEqual(codes["FAM_CHILD"], 30000)      # 10000 x 3

	def test_missing_family_has_no_family_allowances(self):
		codes, _ = self._codes(spouse_eligible=False, children_count=0)
		self.assertNotIn("FAM_SPOUSE", codes)
		self.assertNotIn("FAM_CHILD", codes)

	def test_family_raises_gross_and_net(self):
		_, plain = self._codes()
		_, withfam = self._codes(spouse_eligible=True, children_count=2)
		self.assertGreater(withfam.gross_salary, plain.gross_salary)
		self.assertGreater(withfam.net_salary, plain.net_salary)


class TestMissingDataErrors(unittest.TestCase):
	def test_missing_grade_stage_raises(self):
		# a grade/stage not present in the scale must raise (never silently 0)
		with self.assertRaises(PayrollError):
			compute_net_salary(ctx(), emp("999", 1))
		with self.assertRaises(PayrollError):
			compute_net_salary(ctx(), emp("7", 99))

	def test_missing_grade_value_raises(self):
		from iraqi_government_payroll.services.payroll_engine.scale_resolver import resolve_grade_code
		with self.assertRaises(PayrollError):
			resolve_grade_code(None, None)

	def test_missing_rule_set_for_period_raises(self):
		# a period date with no active rule set must raise (no fabricated rule set)
		with self.assertRaises(PayrollError):
			compute_net_salary(ctx(), emp("7", 1, period_date="1990-01-01"))


class TestSnapshotPayload(unittest.TestCase):
	def test_active_salary_snapshot_structure(self):
		e = emp("7", 1, spouse_eligible=True, children_count=2)
		active = calculate_active_salary(ctx(), e)
		snap = build_snapshot_payload(active, employee_input=e, employee_profile="E1")
		self.assertEqual(snap["doctype"], "Payroll Calculation Snapshot")
		self.assertEqual(snap["grade_code"], "7")
		self.assertEqual(snap["gross_amount"], active.gross_salary)
		inp = json.loads(snap["input_snapshot"])
		self.assertEqual(inp["grade_code"], "7")
		self.assertTrue(inp["spouse_eligible"])
		out = json.loads(snap["output_snapshot"])
		self.assertIn("basic_salary", out)
		self.assertIn("allowance_lines", out)


if __name__ == "__main__":
	unittest.main()
