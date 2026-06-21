# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for M7 Payroll Period validation + Payroll Run batch (pure, no bench).

Run:  python3 -m unittest test_payroll_run -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine.engine import DataContext  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.payroll_run import (  # noqa: E402
	run_payroll_batch, STATUS_FAILED, STATUS_COMPLETED_WITH_WARNINGS,
)
from iraqi_government_payroll.services.payroll_engine.payroll_period import (  # noqa: E402
	validate_period_dates, validate_status_transition, check_duplicate,
)
from iraqi_government_payroll.services.payroll_engine.types import PayrollError  # noqa: E402


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


class FakeSlipStore:
	def __init__(self):
		self.slips = {}          # (period, employee) -> slip dict
		self.snapshots = []      # never written in M7 (draft only)

	def upsert(self, period, run, employee, rule_set, result):
		key = (period, employee)
		created = key not in self.slips
		self.slips[key] = {
			"payroll_period": period, "payroll_run": run, "employee_profile": employee,
			"rule_set": rule_set, "basic_salary": result.basic_salary,
			"total_earnings": result.gross_salary, "total_deductions": result.total_deductions,
			"net_salary": result.net_salary, "status": "Draft",
		}
		return f"SAL-{employee}", created


def profiles(n=2, bad=False):
	out = [{"name": f"EMP-{i}", "grade_code": "7", "current_stage": 1, "qualification": "Bachelor"}
		   for i in range(1, n + 1)]
	if bad:
		out.append({"name": "EMP-BAD", "grade_code": "99", "current_stage": 1, "qualification": "Bachelor"})
	return out


PERIOD = "PP-2020-6"


class TestPayrollPeriodValidation(unittest.TestCase):
	def test_valid_dates(self):
		self.assertTrue(validate_period_dates(2020, 6, "2020-06-01", "2020-06-30"))

	def test_start_after_end_raises(self):
		with self.assertRaises(PayrollError):
			validate_period_dates(2020, 6, "2020-06-30", "2020-06-01")

	def test_range_must_match_month_year(self):
		with self.assertRaises(PayrollError):
			validate_period_dates(2020, 6, "2020-07-01", "2020-07-31")

	def test_status_flow(self):
		self.assertTrue(validate_status_transition("Draft", "Open"))
		self.assertTrue(validate_status_transition("Open", "Closed"))
		with self.assertRaises(PayrollError):
			validate_status_transition("Closed", "Open")
		with self.assertRaises(PayrollError):
			validate_status_transition("Draft", "Closed")

	def test_duplicate_detection(self):
		with self.assertRaises(PayrollError):
			check_duplicate(2020, 6, [(2019, 1), (2020, 6)])
		self.assertTrue(check_duplicate(2020, 7, [(2020, 6)]))


class TestPayrollRunBatch(unittest.TestCase):
	def test_creates_slips_for_eligible_employees(self):
		store = FakeSlipStore()
		r = run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", profiles(2), ctx(), store, "2020-06-01")
		self.assertEqual(r.total_employees, 2)
		self.assertEqual(r.processed_count, 2)
		self.assertEqual(len(store.slips), 2)
		self.assertTrue(all(o.created for o in r.outcomes))
		self.assertEqual(r.status, STATUS_COMPLETED_WITH_WARNINGS)   # PC-6/7 warnings

	def test_idempotency_no_duplicate_slips(self):
		store = FakeSlipStore()
		run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", profiles(2), ctx(), store, "2020-06-01")
		r2 = run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", profiles(2), ctx(), store, "2020-06-01")
		self.assertEqual(len(store.slips), 2)                        # not 4
		self.assertTrue(all(not o.created for o in r2.outcomes))     # updated, not created

	def test_single_employee_warning_completed_with_warnings(self):
		store = FakeSlipStore()
		r = run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", profiles(1), ctx(), store, "2020-06-01")
		self.assertEqual(r.warning_count, 1)
		self.assertEqual(r.status, STATUS_COMPLETED_WITH_WARNINGS)

	def test_all_errors_failed(self):
		store = FakeSlipStore()
		bad = [{"name": "EMP-BAD", "grade_code": "99", "current_stage": 1, "qualification": "Bachelor"}]
		r = run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", bad, ctx(), store, "2020-06-01")
		self.assertEqual(r.error_count, 1)
		self.assertEqual(r.status, STATUS_FAILED)
		self.assertEqual(len(store.slips), 0)

	def test_mixed_error_completed_with_warnings(self):
		store = FakeSlipStore()
		r = run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", profiles(1, bad=True), ctx(), store, "2020-06-01")
		self.assertEqual(r.error_count, 1)
		self.assertEqual(r.processed_count, 1)
		self.assertEqual(r.status, STATUS_COMPLETED_WITH_WARNINGS)
		self.assertTrue(any(o.error for o in r.outcomes))

	def test_salary_slip_fields_populated(self):
		store = FakeSlipStore()
		run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", profiles(1), ctx(), store, "2020-06-01")
		slip = store.slips[(PERIOD, "EMP-1")]
		self.assertEqual(slip["basic_salary"], 296000)
		self.assertEqual(slip["total_earnings"], 429200)
		# net = gross(429200) - pension(5% of basic = 14800, provisional) - tax(57713) = 356687
		# Pension deduction: DED_PENSION confirmed=0, percentage=5 (PC-6 provisional placeholder).
		self.assertEqual(slip["total_deductions"], 72513)           # 14800 pension + 57713 tax
		self.assertEqual(slip["net_salary"], 356687)
		self.assertEqual(slip["status"], "Draft")

	def test_no_snapshots_for_draft_slips(self):
		store = FakeSlipStore()
		run_payroll_batch(PERIOD, "PR-1", "IRAQ-2015", profiles(2), ctx(), store, "2020-06-01")
		self.assertEqual(store.snapshots, [])                        # no snapshot on draft


if __name__ == "__main__":
	unittest.main()
