# Copyright (c) 2026, Iraqi Government Payroll
"""Backend functional tests — Retirement Pension matrix (item 5).

Service-year sweep (15/20/30/35), certificate levels (Bachelor/Master/Doctorate),
cost-of-living, end-of-service, pension tax and net pension. Pure (no bench).
IRAQ-2015 rule: accrual 2.5%/yr, cap 100% of last functional salary, EOS at ≥30
years. Run:  python3 -m unittest test_pension_cases -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.pension.pension_service import (  # noqa: E402
	compute_retirement_pension, RetirementPensionInput,
)


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


PENSION_RULE = fx("pension_rule.json")[0]
ALLOWANCES = fx("allowance_rule.json")
BRACKETS = fx("income_tax_bracket.json")

AVG = 1_010_000
LAST = 1_030_000


def pin(**over):
	base = dict(avg36=AVG, service_years=30, extra_months=0,
				last_functional_salary=LAST, last_full_salary=LAST, qualification="Bachelor")
	base.update(over)
	return RetirementPensionInput(**base)


def compute(**over):
	return compute_retirement_pension(pin(**over), PENSION_RULE, ALLOWANCES, BRACKETS)


class TestServiceYears(unittest.TestCase):
	def test_approved_scales_with_service(self):
		# accrual 2.5%/yr on the 36-month average, capped at last functional salary
		self.assertEqual(compute(service_years=15).approved_pension, 378750)   # 1,010,000 * .025 * 15
		self.assertEqual(compute(service_years=20).approved_pension, 505000)   # * .025 * 20
		self.assertEqual(compute(service_years=30).approved_pension, 757500)   # * .025 * 30
		self.assertEqual(compute(service_years=35).approved_pension, 883750)   # * .025 * 35

	def test_approved_is_monotonic(self):
		vals = [compute(service_years=y).approved_pension for y in (15, 20, 30, 35)]
		self.assertEqual(vals, sorted(vals))

	def test_cap_at_100pct_of_last_salary(self):
		# 50 years would be 125% of avg; capped at 100% of last functional salary
		r = compute(service_years=50)
		self.assertLessEqual(r.approved_pension, LAST)

	def test_eos_only_at_or_above_threshold(self):
		self.assertEqual(compute(service_years=15).end_of_service_bonus, 0)
		self.assertEqual(compute(service_years=20).end_of_service_bonus, 0)
		# EOS = last full salary x 12 once service >= 30
		self.assertEqual(compute(service_years=30).end_of_service_bonus, LAST * 12)
		self.assertEqual(compute(service_years=35).end_of_service_bonus, LAST * 12)


class TestCertificateLevels(unittest.TestCase):
	def test_certificate_increases_with_qualification(self):
		b = compute(qualification="Bachelor")
		m = compute(qualification="Master")
		d = compute(qualification="Doctorate")
		# 10% / 15% / 20% of the approved pension
		self.assertEqual(b.certificate_allowance, round(b.approved_pension * 0.10))
		self.assertEqual(m.certificate_allowance, round(m.approved_pension * 0.15))
		self.assertEqual(d.certificate_allowance, round(d.approved_pension * 0.20))
		self.assertLess(b.certificate_allowance, m.certificate_allowance)
		self.assertLess(m.certificate_allowance, d.certificate_allowance)

	def test_unknown_qualification_zero_certificate_with_warning(self):
		r = compute(qualification="NONE-XYZ")
		self.assertEqual(r.certificate_allowance, 0)
		self.assertTrue(any("certificate" in w.lower() for w in r.warnings))


class TestColTaxNet(unittest.TestCase):
	def test_cost_of_living_applied_when_configured(self):
		r = compute(cost_of_living_method="Fixed Percentage", cost_of_living_value=30)
		self.assertGreater(r.cost_of_living, 0)

	def test_cost_of_living_zero_when_missing(self):
		r = compute(cost_of_living_method=None, cost_of_living_value=None)
		self.assertEqual(r.cost_of_living, 0)

	def test_gross_and_net_reconcile(self):
		r = compute(service_years=30, cost_of_living_method="Fixed Percentage", cost_of_living_value=30)
		self.assertEqual(r.gross_pension, r.approved_pension + r.certificate_allowance + r.cost_of_living)
		self.assertEqual(r.net_pension, r.gross_pension - r.monthly_tax - r.other_deductions)
		self.assertGreaterEqual(r.monthly_tax, 0)
		self.assertGreater(r.net_pension, 0)


if __name__ == "__main__":
	unittest.main()
