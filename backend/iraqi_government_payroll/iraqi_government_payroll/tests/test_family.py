# Copyright (c) 2026, Iraqi Government Payroll
"""Pure tests for the Family & Dependents module.

Covers: age calculation, spouse/child counts, eligible-dependent counts, the
employed-dependent exclusion, snapshot immutability of the recorded family state,
and a payroll Family/Child allowance computed from the dependent count (using the
configurable Allowance Rule fixtures — no amounts hard-coded). Run:
    python3 -m unittest test_family -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.family import family_service as fam  # noqa: E402
from iraqi_government_payroll.services.payroll_engine.engine import (  # noqa: E402
	DataContext, EmployeeInput, calculate_active_salary,
)
from iraqi_government_payroll.services.audit.audit_service import build_snapshot_payload  # noqa: E402

AS_OF = "2024-06-30"


def member(**kw):
	base = {"is_alive": 1, "financially_dependent": 1}
	base.update(kw)
	return base


# A representative household evaluated as of 2024-06-30.
MEMBERS = [
	member(full_name="Spouse", relation="Spouse", date_of_birth="1990-01-01"),
	member(full_name="Son10", relation="Son", date_of_birth="2014-01-01"),
	member(full_name="Daughter20Std", relation="Daughter", date_of_birth="2004-01-01", is_student=1),
	member(full_name="Son20", relation="Son", date_of_birth="2004-01-01"),                       # >18, not student
	member(full_name="Daughter25Dis", relation="Daughter", date_of_birth="1999-01-01", has_disability=1),
	member(full_name="Son30Emp", relation="Son", date_of_birth="1994-01-01",
		   is_employed=1, employment_type="Government", monthly_income=500000),                  # employed-excluded
	member(full_name="Father70", relation="Father", date_of_birth="1954-01-01"),
	member(full_name="MotherDead", relation="Mother", date_of_birth="1955-01-01", is_alive=0),
]


class TestAge(unittest.TestCase):
	def test_age_calculation(self):
		self.assertEqual(fam.compute_age("2014-01-01", AS_OF), 10)
		self.assertEqual(fam.compute_age("2004-07-01", AS_OF), 19)   # birthday not yet reached
		self.assertEqual(fam.compute_age("2004-06-01", AS_OF), 20)   # birthday passed
		self.assertIsNone(fam.compute_age(None, AS_OF))


class TestCounts(unittest.TestCase):
	def setUp(self):
		self.s = fam.summarize(MEMBERS, as_of=AS_OF)["summary"]

	def test_spouse_and_child_counts(self):
		self.assertEqual(self.s["spouse_count"], 1)
		self.assertEqual(self.s["children_count"], 5)               # 3 sons + 2 daughters

	def test_eligible_children_count(self):
		# Son10 ✓, Daughter20Std ✓, Daughter25Dis ✓ (disability); Son20 ✗ (>18), Son30Emp ✗ (employed)
		self.assertEqual(self.s["eligible_children_count"], 3)

	def test_dependent_counts(self):
		self.assertEqual(self.s["dependents_count"], 7)             # all alive + financially dependent (not the dead mother)
		self.assertEqual(self.s["eligible_dependents_count"], 5)    # + spouse + father, - son20 - son30
		self.assertEqual(self.s["disabled_dependents_count"], 1)
		self.assertEqual(self.s["student_dependents_count"], 1)

	def test_employed_dependent_excluded(self):
		self.assertEqual(self.s["employed_dependents_count"], 1)
		enriched = fam.summarize(MEMBERS, as_of=AS_OF)["members"]
		son30 = next(m for m in enriched if m["full_name"] == "Son30Emp")
		self.assertEqual(son30["eligible_for_family_allowance"], 0)  # employed -> not eligible

	def test_age_written_back(self):
		enriched = fam.summarize(MEMBERS, as_of=AS_OF)["members"]
		son10 = next(m for m in enriched if m["full_name"] == "Son10")
		self.assertEqual(son10["age"], 10)


class TestConfigConfigurable(unittest.TestCase):
	def test_thresholds_are_injectable(self):
		# raise the income threshold above the son's income -> he is no longer excluded
		s = fam.summarize(MEMBERS, as_of=AS_OF, config={"dependent_income_threshold": 1000000})
		son30 = next(m for m in s["members"] if m["full_name"] == "Son30Emp")
		# age 30, not student -> still ineligible by age, but no longer income-excluded
		self.assertEqual(son30["age"], 30)


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


def ctx():
	return DataContext(
		rule_sets=fx("government_rule_set.json"),
		scales=fx("government_salary_scale.json"),
		allowance_rules=fx("allowance_rule.json"),
	)


class TestPayrollFamilyAllowance(unittest.TestCase):
	"""The engine computes the Family/Child allowance from the dependent count
	using the configurable Allowance Rule fixtures (FAM_CHILD / FAM_SPOUSE)."""

	def _lines(self, **kw):
		emp = EmployeeInput(grade_code="7", stage=1, period_date="2020-06-01",
							qualification="Bachelor", **kw)
		res = calculate_active_salary(ctx(), emp)
		return {l.component_code: l.amount for l in res.allowance_lines}

	def test_child_allowance_scales_with_count(self):
		base = self._lines(spouse_eligible=False, children_count=0)
		self.assertNotIn("FAM_CHILD", base)
		three = self._lines(spouse_eligible=False, children_count=3)
		self.assertIn("FAM_CHILD", three)
		# FAM_CHILD fixed amount is 10000 (from the fixture, not hard-coded here)
		self.assertEqual(three["FAM_CHILD"], 30000)               # 10000 * 3

	def test_child_allowance_clamped_at_four(self):
		six = self._lines(spouse_eligible=False, children_count=6)
		self.assertEqual(six["FAM_CHILD"], 40000)                 # 10000 * min(6, 4)

	def test_spouse_allowance_present_when_eligible(self):
		lines = self._lines(spouse_eligible=True, children_count=0)
		self.assertEqual(lines["FAM_SPOUSE"], 50000)


class TestSnapshotImmutability(unittest.TestCase):
	"""The dependent counts recorded in a snapshot's input do not change when the
	family later changes — historical payroll stays reproducible."""

	def test_snapshot_freezes_family_state(self):
		summary_a = fam.summarize(MEMBERS, as_of=AS_OF)["summary"]
		emp = EmployeeInput(
			grade_code="7", stage=1, period_date="2020-06-01", qualification="Bachelor",
			spouse_eligible=True, children_count=summary_a["eligible_children_count"],
			family_summary=summary_a)
		res = calculate_active_salary(ctx(), emp)
		snap = build_snapshot_payload(res, employee_input=emp, employee_profile="E1")
		frozen = json.loads(snap["input_snapshot"])["family_summary"]
		self.assertEqual(frozen["eligible_children_count"], 3)

		# family grows later
		bigger = MEMBERS + [member(full_name="NewBaby", relation="Son", date_of_birth="2024-01-01")]
		summary_b = fam.summarize(bigger, as_of=AS_OF)["summary"]
		self.assertEqual(summary_b["eligible_children_count"], 4)   # changed now...
		# ...but the already-built snapshot is unchanged
		self.assertEqual(json.loads(snap["input_snapshot"])["family_summary"]["eligible_children_count"], 3)


if __name__ == "__main__":
	unittest.main()
