# Copyright (c) 2026, Iraqi Government Payroll
"""Unit tests for the M3 Core Active Salary Engine.

Pure tests: they load the M2 fixtures directly and exercise the engine without a
Frappe bench. Run:  python3 -m unittest test_active_salary -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # backend/iraqi_government_payroll
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine.engine import (  # noqa: E402
	DataContext, EmployeeInput, calculate_active_salary,
)
from iraqi_government_payroll.services.payroll_engine.rule_resolver import resolve_rule_set  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.scale_resolver import (  # noqa: E402
	get_basic_salary, resolve_grade_code,
)
from iraqi_government_payroll.services.payroll_engine.types import (  # noqa: E402
	PayrollError, AllowanceLine, ENGINE_VERSION,
)
from iraqi_government_payroll.services.allowance.allowance_service import apply_200_cap  # noqa: E402
from iraqi_government_payroll.services.audit.audit_service import build_snapshot_payload  # noqa: E402


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


def ctx():
	return DataContext(
		rule_sets=fx("government_rule_set.json"),
		scales=fx("government_salary_scale.json"),
		allowance_rules=fx("allowance_rule.json"),
	)


SCALE_DETAILS = fx("government_salary_scale.json")[0]["details"]


class TestRuleSetResolver(unittest.TestCase):
	def test_resolves_single_active(self):
		rs = resolve_rule_set(fx("government_rule_set.json"), "2020-06-01")
		self.assertEqual(rs["name"], "IRAQ-2015")

	def test_none_active_raises(self):
		# 2010 predates IRAQ-2015; IRAQ-2008 is Archived (not Active)
		with self.assertRaises(PayrollError):
			resolve_rule_set(fx("government_rule_set.json"), "2010-01-01")

	def test_multiple_active_raises(self):
		two = [
			{"name": "A", "status": "Active", "effective_from": "2015-01-01", "effective_to": None},
			{"name": "B", "status": "Active", "effective_from": "2016-01-01", "effective_to": None},
		]
		with self.assertRaises(PayrollError):
			resolve_rule_set(two, "2020-01-01")


class TestSalaryScaleResolver(unittest.TestCase):
	def test_regular_lookup(self):
		self.assertEqual(get_basic_salary(SCALE_DETAILS, "7", 1), 296000)
		self.assertEqual(get_basic_salary(SCALE_DETAILS, "10", 1), 170000)
		self.assertEqual(get_basic_salary(SCALE_DETAILS, "6", 3), 374000)

	def test_senior_lookup(self):
		self.assertEqual(get_basic_salary(SCALE_DETAILS, "SPECIAL_A", 1), 2413000)
		self.assertEqual(get_basic_salary(SCALE_DETAILS, "SPECIAL_C", 11), 2330000)

	def test_missing_row_raises(self):
		with self.assertRaises(PayrollError):
			get_basic_salary(SCALE_DETAILS, "99", 1)


class TestAnchorCertificate(unittest.TestCase):
	def test_bachelor_grade7_stage1(self):
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01", qualification="Bachelor")
		r = calculate_active_salary(ctx(), emp)
		self.assertEqual(r.basic_salary, 296000)
		cert = [l for l in r.allowance_lines if l.component_code == "CERT_ACT_BACHELOR"]
		self.assertEqual(len(cert), 1)
		self.assertEqual(cert[0].amount, 133200)          # 296000 * 45%
		self.assertEqual(r.capped_allowance_total, 133200)
		self.assertEqual(r.gross_salary, 429200)          # 296000 + 133200
		self.assertEqual(r.engine_version, ENGINE_VERSION)
		self.assertEqual(r.rule_set, "IRAQ-2015")


class TestCertificateNoMatch(unittest.TestCase):
	def test_no_certificate_allowance_is_zero_with_warning(self):
		# "Primary" has no certificate allowance rule in the fixtures
		emp = EmployeeInput(grade_code="10", stage=1, period_date="2020-06-01", qualification="Primary")
		r = calculate_active_salary(ctx(), emp)
		self.assertEqual([l for l in r.allowance_lines if l.match_key == "Qualification"], [])
		self.assertEqual(r.capped_allowance_total, 0)
		self.assertEqual(r.gross_salary, r.basic_salary)  # 170000
		self.assertTrue(any("Primary" in w for w in r.warnings))


class TestCap(unittest.TestCase):
	def test_cap_limits_capped_allowances_to_200pct_of_basic(self):
		# 200% cap: total CAPPED allowances may not exceed 200% of basic (2 x basic).
		basic = 100000
		lines = [
			AllowanceLine("A", "A", "Earning", "Qualification", 150000, basic, 150, capped=True),
			AllowanceLine("B", "B", "Earning", "Position Allowance Category", 120000, basic, 120, capped=True),
			AllowanceLine("F", "F", "Earning", "Family", 50000, 0, None, capped=False),
		]
		allowed, non_capped, excluded, warns = apply_200_cap(lines, basic)
		self.assertEqual(allowed, 200000)        # 200% of 100000 (= 2 x basic)
		self.assertEqual(non_capped, 50000)
		self.assertEqual(excluded, 70000)        # 270000 - 200000
		self.assertTrue(warns)
		self.assertTrue(all(l.cap_applied for l in lines if l.capped))

	def test_cap_not_applied_when_within(self):
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01", qualification="Bachelor")
		r = calculate_active_salary(ctx(), emp)
		self.assertEqual(r.cap_excluded_amount, 0)
		self.assertFalse(any(l.cap_applied for l in r.allowance_lines))


class TestConfirmedFalseBehaviour(unittest.TestCase):
	def test_value_present_is_provisional(self):
		# FAM_SPOUSE: confirmed=false, fixed_amount=50000 -> compute + provisional flag
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01",
							qualification="Bachelor", spouse_eligible=True)
		r = calculate_active_salary(ctx(), emp)
		spouse = [l for l in r.allowance_lines if l.component_code == "FAM_SPOUSE"]
		self.assertEqual(len(spouse), 1)
		self.assertEqual(spouse[0].amount, 50000)
		self.assertTrue(spouse[0].provisional)
		self.assertIn("FAM_SPOUSE", r.provisional_flags)
		self.assertEqual(r.non_capped_allowance_total, 50000)

	def test_children_capped_at_four_provisional(self):
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01",
							qualification="Bachelor", children_count=6)
		r = calculate_active_salary(ctx(), emp)
		child = [l for l in r.allowance_lines if l.component_code == "FAM_CHILD"]
		self.assertEqual(len(child), 1)
		self.assertEqual(child[0].amount, 40000)          # min(6,4) * 10000
		self.assertIn("FAM_CHILD", r.provisional_flags)

	def test_empty_value_is_skipped_with_warning(self):
		# RISK_DEFAULT: confirmed=false, no percentage -> skipped + warning
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01",
							qualification="Bachelor", risk_applicable=True, risk_category="GENERAL")
		r = calculate_active_salary(ctx(), emp)
		self.assertEqual([l for l in r.allowance_lines if l.match_key == "Risk Category"], [])
		self.assertTrue(any("RISK_DEFAULT" in w for w in r.warnings))


class TestDeductionsExcluded(unittest.TestCase):
	def test_ded_tax_not_in_active_result(self):
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01", qualification="Bachelor")
		r = calculate_active_salary(ctx(), emp)
		codes = [l.component_code for l in r.allowance_lines]
		self.assertNotIn("DED_TAX", codes)
		self.assertFalse(any(c.startswith("DED_") for c in codes))
		self.assertFalse(any(l.line_type == "Deduction" for l in r.allowance_lines))
		self.assertEqual(r.gross_salary, 429200)          # unaffected by any deduction


class TestSnapshotPayload(unittest.TestCase):
	def test_payload_structure(self):
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01", qualification="Bachelor")
		r = calculate_active_salary(ctx(), emp)
		p = build_snapshot_payload(r, employee_input=emp, employee_profile="EMP-0001")
		for key in ("doctype", "rule_set", "engine_version", "period_date",
					"input_snapshot", "output_snapshot", "lines", "gross_amount",
					"total_deductions", "net_amount"):
			self.assertIn(key, p)
		self.assertEqual(p["doctype"], "Payroll Calculation Snapshot")
		self.assertEqual(p["rule_set"], "IRAQ-2015")
		self.assertEqual(p["engine_version"], ENGINE_VERSION)
		self.assertEqual(p["total_deductions"], 0)        # M3: no deductions
		self.assertEqual(p["net_amount"], p["gross_amount"])
		self.assertIsInstance(p["lines"], list)
		self.assertTrue(all("component_code" in ln and "amount" in ln for ln in p["lines"]))
		json.loads(p["input_snapshot"])                   # valid JSON
		json.loads(p["output_snapshot"])


class TestGradeCodeResolution(unittest.TestCase):
	def test_regular_grade_uses_grade_code(self):
		# grade_code is authoritative even if current_grade differs
		self.assertEqual(resolve_grade_code("7", 5), "7")
		self.assertEqual(resolve_grade_code("10", 2), "10")

	def test_senior_grade_code(self):
		self.assertEqual(resolve_grade_code("SPECIAL_A", None), "SPECIAL_A")
		self.assertEqual(resolve_grade_code("SPECIAL_C", 0), "SPECIAL_C")

	def test_fallback_to_current_grade_only_when_missing(self):
		self.assertEqual(resolve_grade_code("", 7), "7")
		self.assertEqual(resolve_grade_code(None, 10), "10")

	def test_no_grade_at_all_raises(self):
		with self.assertRaises(PayrollError):
			resolve_grade_code("", None)


class TestSeniorGradeEngine(unittest.TestCase):
	def test_special_a_grade_engine(self):
		# Senior grade resolved via grade_code SPECIAL_A; no qualification -> cert 0
		gc = resolve_grade_code("SPECIAL_A", None)
		emp = EmployeeInput(grade_code=gc, stage=1, period_date="2020-06-01")
		r = calculate_active_salary(ctx(), emp)
		self.assertEqual(r.grade_code, "SPECIAL_A")
		self.assertEqual(r.basic_salary, 2413000)
		self.assertEqual(r.gross_salary, 2413000)


if __name__ == "__main__":
	unittest.main()
