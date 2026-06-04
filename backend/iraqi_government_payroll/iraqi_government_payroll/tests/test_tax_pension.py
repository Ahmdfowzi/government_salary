# Copyright (c) 2026, Iraqi Government Payroll
"""Unit tests for the M4 Tax & Pension engines (pure, no bench).

Run:  python3 -m unittest test_tax_pension -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # backend/iraqi_government_payroll
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.tax.tax_service import (  # noqa: E402
	compute_annual_tax, compute_monthly_tax, round_iqd, resolve_legal_allowances,
)
from iraqi_government_payroll.services.pension.pension_service import (  # noqa: E402
	compute_pension_deduction, compute_retirement_pension, RetirementPensionInput,
)
from iraqi_government_payroll.services.audit.audit_service import (  # noqa: E402
	build_retirement_pension_snapshot_payload,
)


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


BRACKETS = fx("income_tax_bracket.json")
PENSION_RULE = fx("pension_rule.json")[0]
ALLOWANCES = fx("allowance_rule.json")
TAX_ALLOWANCES = fx("tax_allowance_rule.json")
DED_PENSION = next(r for r in ALLOWANCES if r["component_code"] == "DED_PENSION")


class TestTaxEngine(unittest.TestCase):
	def test_anchor_taxable_to_monthly(self):
		self.assertEqual(compute_annual_tax(14_725_800, BRACKETS), 2_128_870)
		self.assertEqual(round_iqd(2_128_870 / 12.0), 177_406)
		r = compute_monthly_tax(1_227_150, BRACKETS)   # gross x12 = 14,725,800
		self.assertEqual(r["annual_tax"], 2_128_870)
		self.assertEqual(r["monthly_tax"], 177_406)

	def test_bracket_boundaries(self):
		self.assertEqual(compute_annual_tax(0, BRACKETS), 0)
		self.assertEqual(compute_annual_tax(250_000, BRACKETS), 7_500)
		self.assertEqual(compute_annual_tax(500_000, BRACKETS), 20_000)
		self.assertEqual(compute_annual_tax(1_000_000, BRACKETS), 70_000)

	def test_taxable_never_negative(self):
		r = compute_monthly_tax(100_000, BRACKETS, legal_allowances=5_000_000)
		self.assertEqual(r["taxable_annual"], 0)
		self.assertEqual(r["monthly_tax"], 0)

	def test_missing_allowances_taxable_equals_gross(self):
		total, warnings, provisional = resolve_legal_allowances(TAX_ALLOWANCES, "Single")
		self.assertEqual(total, 0)            # PC-7/8 pending -> empty
		self.assertTrue(warnings)
		r = compute_monthly_tax(1_227_150, BRACKETS, legal_allowances=total)
		self.assertEqual(r["taxable_annual"], 14_725_800)   # == annual gross


class TestPensionDeduction(unittest.TestCase):
	def test_missing_pc6_skipped_with_warning(self):
		d = compute_pension_deduction(296_000, DED_PENSION)   # confirmed=false, empty
		self.assertEqual(d["amount"], 0)
		self.assertTrue(d["skipped"])
		self.assertTrue(any("PC-6" in w for w in d["warnings"]))

	def test_provided_rate_computes(self):
		rule = {"component_code": "DED_PENSION", "percentage": 10, "confirmed": 1}
		d = compute_pension_deduction(296_000, rule)
		self.assertEqual(d["amount"], 29_600)
		self.assertFalse(d["skipped"])

	def test_provisional_rate(self):
		rule = {"component_code": "DED_PENSION", "percentage": 7, "confirmed": 0}
		d = compute_pension_deduction(100_000, rule)
		self.assertEqual(d["amount"], 7_000)
		self.assertTrue(d["provisional"])


def anchor_input(**over):
	base = dict(avg36=1_010_000, service_years=36, extra_months=0,
				last_functional_salary=1_030_000, last_full_salary=1_030_000,
				qualification="Bachelor", cost_of_living_method="Fixed Percentage",
				cost_of_living_value=25, rule_set="IRAQ-2015")
	base.update(over)
	return RetirementPensionInput(**base)


class TestRetirementPension(unittest.TestCase):
	def test_full_anchor(self):
		r = compute_retirement_pension(anchor_input(), PENSION_RULE, ALLOWANCES, BRACKETS)
		self.assertEqual(r.service_months, 432)
		self.assertEqual(r.initial_pension, 909_000)
		self.assertEqual(r.approved_pension, 909_000)
		self.assertEqual(r.certificate_allowance, 90_900)
		self.assertEqual(r.cost_of_living, 227_250)
		self.assertEqual(r.gross_pension, 1_227_150)
		self.assertEqual(r.monthly_tax, 177_406)
		self.assertEqual(r.net_pension, 1_049_744)
		self.assertEqual(r.end_of_service_bonus, 12_360_000)

	def test_100pct_cap_binds(self):
		r = compute_retirement_pension(
			anchor_input(last_functional_salary=800_000), PENSION_RULE, ALLOWANCES, BRACKETS)
		self.assertEqual(r.initial_pension, 909_000)
		self.assertEqual(r.approved_pension, 800_000)   # capped at last functional salary

	def test_eos_zero_below_30_years(self):
		r = compute_retirement_pension(
			anchor_input(service_years=20), PENSION_RULE, ALLOWANCES, BRACKETS)
		self.assertEqual(r.end_of_service_bonus, 0)

	def test_certificate_no_match(self):
		r = compute_retirement_pension(
			anchor_input(qualification="Primary"), PENSION_RULE, ALLOWANCES, BRACKETS)
		self.assertEqual(r.certificate_allowance, 0)
		self.assertTrue(any("Primary" in w for w in r.warnings))

	def test_cost_of_living_missing(self):
		# No override + pension_rule fixture method is empty (PC-9) -> COL 0 + warning
		r = compute_retirement_pension(
			anchor_input(cost_of_living_method=None, cost_of_living_value=None),
			PENSION_RULE, ALLOWANCES, BRACKETS)
		self.assertEqual(r.cost_of_living, 0)
		self.assertTrue(any("PC-9" in w for w in r.warnings))

	def test_snapshot_payload_structure(self):
		r = compute_retirement_pension(anchor_input(), PENSION_RULE, ALLOWANCES, BRACKETS)
		p = build_retirement_pension_snapshot_payload(r, employee_profile="EMP-0001")
		for key in ("doctype", "calculation_type", "rule_set", "engine_version",
					"period_date", "input_snapshot", "output_snapshot", "lines",
					"gross_amount", "total_deductions", "net_amount"):
			self.assertIn(key, p)
		self.assertEqual(p["doctype"], "Payroll Calculation Snapshot")
		self.assertEqual(p["calculation_type"], "Retirement Pension")
		self.assertEqual(p["net_amount"], 1_049_744)
		self.assertIsInstance(p["lines"], list)
		json.loads(p["input_snapshot"])
		json.loads(p["output_snapshot"])


if __name__ == "__main__":
	unittest.main()
