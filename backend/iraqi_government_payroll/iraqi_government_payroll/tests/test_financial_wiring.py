# Copyright (c) 2026, Iraqi Government Payroll
"""End-to-end FINANCIAL WIRING tests (pure, fixture-backed).

Confirms the financial chain is actually connected: rule set → salary scale →
grade/stage → basic → allowance rules → 200% cap → gross → pension deduction →
income tax → net; the family→child-allowance link; the payroll-run batch
aggregation; and that the dependents summary is carried into the snapshot input.
Run:  python3 -m unittest test_financial_wiring -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine.engine import (  # noqa: E402
	DataContext, EmployeeInput,
)
from iraqi_government_payroll.services.payroll_engine.net_salary import compute_net_salary  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.payroll_run import (  # noqa: E402
	run_payroll_batch, employee_input_from_profile,
	STATUS_COMPLETED, STATUS_COMPLETED_WITH_WARNINGS, STATUS_FAILED,
)
from dataclasses import asdict  # noqa: E402


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


def emp(**kw):
	base = dict(grade_code="7", stage=1, period_date="2020-06-01", qualification="Bachelor")
	base.update(kw)
	return EmployeeInput(**base)


class TestNetSalaryChain(unittest.TestCase):
	def test_full_chain_links(self):
		r = compute_net_salary(ctx(), emp())
		# rule set -> scale -> grade/stage -> basic
		self.assertEqual(r.rule_set, "IRAQ-2015")
		self.assertEqual(r.basic_salary, 296000)                 # g7s1 Bachelor anchor
		# basic + allowances = gross
		self.assertEqual(r.gross_salary,
						 r.basic_salary + r.capped_allowance_total + r.non_capped_allowance_total)
		# gross - pension - tax - other = net  (deductions reconcile)
		self.assertEqual(r.total_deductions, r.pension_deduction + r.tax + r.other_deductions)
		self.assertEqual(r.net_salary, r.gross_salary - r.total_deductions)
		# net is never above gross
		self.assertLessEqual(r.net_salary, r.gross_salary)

	def test_pension_and_tax_are_wired(self):
		r = compute_net_salary(ctx(), emp())
		self.assertGreaterEqual(r.pension_deduction, 0)
		self.assertGreaterEqual(r.tax, 0)
		# at least one deduction engine produced a value on a normal salary
		self.assertGreater(r.pension_deduction + r.tax, 0)

	def test_engine_versions_stamped(self):
		r = compute_net_salary(ctx(), emp())
		for k in ("active_salary_engine", "tax_engine", "pension_engine"):
			self.assertIn(k, r.engine_versions)


class TestFamilyAllowanceLink(unittest.TestCase):
	def test_child_allowance_uses_dependent_count(self):
		c = ctx()
		base = {l.component_code: l.amount for l in compute_net_salary(c, emp(children_count=0)).allowance_lines}
		three = {l.component_code: l.amount for l in compute_net_salary(c, emp(children_count=3)).allowance_lines}
		self.assertNotIn("FAM_CHILD", base)
		self.assertEqual(three["FAM_CHILD"], 30000)              # 10000 (rule) x 3 dependents


class TestRunAggregation(unittest.TestCase):
	class FakeStore:
		def __init__(self):
			self.saved = []
		def upsert(self, period, run, employee, rule_set, result):
			self.saved.append((employee, result.net_salary))
			return f"SLIP-{employee}", True

	def _profiles(self):
		return [
			{"name": "E1", "grade_code": "7", "current_stage": 1, "qualification": "Bachelor",
			 "marital_status": "Married", "eligible_children_count": 2},
			{"name": "E2", "grade_code": "5", "current_stage": 3, "qualification": "Master",
			 "marital_status": "Single", "eligible_children_count": 0},
		]

	def test_batch_processes_and_tallies(self):
		store = self.FakeStore()
		res = run_payroll_batch("PERIOD", "RUN", "IRAQ-2015", self._profiles(),
								ctx(), store, "2020-06-01")
		self.assertEqual(res.total_employees, 2)
		self.assertEqual(res.processed_count, 2)
		self.assertEqual(res.error_count, 0)
		self.assertEqual(len(store.saved), 2)
		self.assertIn(res.status, (STATUS_COMPLETED, STATUS_COMPLETED_WITH_WARNINGS))
		for _emp, net in store.saved:
			self.assertGreater(net, 0)

	def test_bad_employee_does_not_abort_batch(self):
		store = self.FakeStore()
		profiles = self._profiles() + [
			{"name": "BAD", "grade_code": "999", "current_stage": 1, "qualification": "Bachelor"}]
		res = run_payroll_batch("PERIOD", "RUN", "IRAQ-2015", profiles, ctx(), store, "2020-06-01")
		self.assertEqual(res.error_count, 1)               # the invalid grade fails alone
		self.assertEqual(res.processed_count, 2)           # the other two still processed
		self.assertNotEqual(res.status, STATUS_FAILED)


class TestSnapshotCarriesInputs(unittest.TestCase):
	def test_run_input_records_family_summary(self):
		profile = {"name": "E1", "grade_code": "7", "current_stage": 1, "qualification": "Bachelor",
				   "marital_status": "Married", "eligible_children_count": 2,
				   "spouse_count": 1, "children_count": 2, "dependents_count": 3,
				   "eligible_dependents_count": 3, "disabled_dependents_count": 0,
				   "employed_dependents_count": 0, "student_dependents_count": 1}
		ein = employee_input_from_profile(profile, "2020-06-01")
		self.assertEqual(ein.family_summary["eligible_children_count"], 2)
		# the run/slip snapshot stores input_snapshot = asdict(employee_input), so the
		# full dependents summary is frozen into the immutable snapshot.
		recorded = asdict(ein)["family_summary"]
		self.assertEqual(recorded["student_dependents_count"], 1)
		self.assertEqual(recorded["spouse_count"], 1)
		# and the payroll still computes (chain intact) for this input
		self.assertGreater(compute_net_salary(ctx(), ein).net_salary, 0)


if __name__ == "__main__":
	unittest.main()
