# Copyright (c) 2026, Iraqi Government Payroll
"""Integration tests for the M5 Net Salary Orchestrator / Salary Slip flow.

Pure tests: load fixtures, run the orchestrator end-to-end without a bench.
Run:  python3 -m unittest test_salary_slip -v
"""

import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine.engine import DataContext, EmployeeInput  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.net_salary import (  # noqa: E402
	compute_net_salary, engine_versions,
)
from iraqi_government_payroll.services.audit.audit_service import (  # noqa: E402
	build_net_salary_snapshot_payload,
)


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


def ctx(pc6_rate=None):
	allow = copy.deepcopy(fx("allowance_rule.json"))
	if pc6_rate is not None:
		for r in allow:
			if r["component_code"] == "DED_PENSION":
				r["percentage"] = pc6_rate
				r["confirmed"] = 1
	return DataContext(
		rule_sets=fx("government_rule_set.json"),
		scales=fx("government_salary_scale.json"),
		allowance_rules=allow,
		income_tax_brackets=fx("income_tax_bracket.json"),
		tax_allowance_rules=fx("tax_allowance_rule.json"),
	)


def bachelor(**over):
	base = dict(grade_code="7", stage=1, period_date="2020-06-01", qualification="Bachelor")
	base.update(over)
	return EmployeeInput(**base)


class TestNetSalaryFlow(unittest.TestCase):
	def test_full_flow_with_pension_and_tax(self):
		# PC-6 confirmed at 10% for this scenario
		r = compute_net_salary(ctx(pc6_rate=10), bachelor())
		self.assertEqual(r.basic_salary, 296000)
		self.assertEqual(r.gross_salary, 429200)        # 296000 + 133200
		self.assertEqual(r.pension_deduction, 29600)    # 296000 * 10%
		self.assertEqual(r.tax, 57713)                  # gross annualized, no allowances
		self.assertEqual(r.total_deductions, 29600 + 57713)
		self.assertEqual(r.net_salary, 429200 - 29600 - 57713)   # 341887

	def test_bachelor_grade7_stage1_full_slip(self):
		# PC-6 pending (fixture) -> pension skipped
		r = compute_net_salary(ctx(), bachelor())
		self.assertEqual(r.basic_salary, 296000)
		self.assertEqual(r.gross_salary, 429200)
		self.assertEqual(r.pension_deduction, 0)
		self.assertEqual(r.tax, 57713)
		self.assertEqual(r.net_salary, 371487)          # 429200 - 0 - 57713


class TestProvisionalAndMissingPC(unittest.TestCase):
	def test_missing_pc6_skips_pension_with_warning(self):
		r = compute_net_salary(ctx(), bachelor())
		self.assertEqual(r.pension_deduction, 0)
		self.assertTrue(any("PC-6" in w for w in r.warnings))

	def test_missing_pc7_taxes_gross_and_flags_provisional(self):
		r = compute_net_salary(ctx(), bachelor())
		self.assertIn("INCOME_TAX", r.provisional_flags)
		self.assertTrue(any("Art.12" in w or "PC-7" in w for w in r.warnings))
		# taxable equals annual gross (no allowance deducted): tax computed on 429200
		self.assertEqual(r.tax, 57713)

	def test_provisional_flag_propagation(self):
		# spouse allowance is confirmed=false-with-value -> provisional propagates to net
		r = compute_net_salary(ctx(), bachelor(spouse_eligible=True))
		self.assertIn("FAM_SPOUSE", r.provisional_flags)
		self.assertEqual(r.non_capped_allowance_total, 50000)
		self.assertEqual(r.gross_salary, 479200)        # 296000 + 133200 + 50000


class TestEngineVersionAndRounding(unittest.TestCase):
	def test_composite_engine_versions(self):
		r = compute_net_salary(ctx(), bachelor())
		self.assertEqual(set(r.engine_versions.keys()),
						 {"active_salary_engine", "tax_engine", "pension_engine"})

	def test_rounding_policy_integers(self):
		r = compute_net_salary(ctx(pc6_rate=7), bachelor())
		for v in (r.basic_salary, r.gross_salary, r.pension_deduction, r.tax,
				  r.total_deductions, r.net_salary):
			self.assertIsInstance(v, int)


class TestSalarySlipSnapshot(unittest.TestCase):
	def test_snapshot_payload_structure(self):
		r = compute_net_salary(ctx(pc6_rate=10), bachelor())
		p = build_net_salary_snapshot_payload(r, employee_profile="EMP-0001", salary_slip="SAL-0001")
		self.assertEqual(p["doctype"], "Payroll Calculation Snapshot")
		self.assertEqual(p["calculation_type"], "Salary Slip")
		self.assertEqual(p["net_amount"], r.net_salary)
		self.assertEqual(p["total_deductions"], r.total_deductions)
		self.assertEqual(p["salary_slip"], "SAL-0001")
		# composite engine version stored as JSON with 3 keys
		ev = json.loads(p["engine_version"])
		self.assertEqual(len(ev), 3)
		# deduction lines present
		codes = [l["component_code"] for l in p["lines"]]
		self.assertIn("DED_PENSION", codes)
		self.assertIn("INCOME_TAX", codes)
		json.loads(p["output_snapshot"])


if __name__ == "__main__":
	unittest.main()
