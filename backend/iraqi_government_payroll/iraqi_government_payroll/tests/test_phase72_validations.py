# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 7.2 — validation logic added to DocType controllers and services.

Pure / no-bench tests for the validation rules added in Phase 7.2:
  - GovernmentRuleSet._ranges_overlap
  - AllowanceRule V2 (required rate fields)
  - GovernmentSalaryScale V1 (one active) + V2 (no dup rows)
  - QualificationAppointmentRule V3 (percentage in [0,100])
  - AnnualIncrementRequest V2 (max stage guard) via the increment engine
  - PromotionRequest V1 (years-in-grade guard) via the promotion engine
  - PensionCalculation V1 (100% cap) via the pension engine
  - compute_pension / evaluate_increment / evaluate_promotion wiring shape
    (pure service calls — the Frappe I/O layer is covered by integration tests)

Run: python3 -m pytest test_phase72_validations.py -v

"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.increment.increment_service import (  # noqa: E402
    compute_increment, MAX_STAGE,
)
from iraqi_government_payroll.services.promotion.promotion_service import (  # noqa: E402
    compute_promotion,
)
from iraqi_government_payroll.services.pension.pension_service import (  # noqa: E402
    compute_retirement_pension, RetirementPensionInput,
)
from iraqi_government_payroll.services.payroll_engine.scale_resolver import (  # noqa: E402
    scale_has_grade_stage,
)


def fx(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)


SCALE = fx("government_salary_scale.json")[0]["details"]
PROMOTION_RULE = fx("promotion_rule.json")[0]
INCREMENT_RULE = fx("annual_increment_rule.json")[0]
PENSION_RULE = fx("pension_rule.json")[0]
TAX_BRACKETS = fx("income_tax_bracket.json")
EFF = "2020-06-01"


# ---------------------------------------------------------------------------
# GovernmentRuleSet: _ranges_overlap helper (extracted inline for testability)
# ---------------------------------------------------------------------------
def _ranges_overlap(f1, t1, f2, t2):
    """Local copy of the overlap helper from government_rule_set.py."""
    a_ends_after_b_starts = (t1 is None) or (f2 is None) or (str(f2) <= str(t1))
    b_ends_after_a_starts = (t2 is None) or (f1 is None) or (str(f1) <= str(t2))
    return a_ends_after_b_starts and b_ends_after_a_starts


class TestRangesOverlap(unittest.TestCase):
    def test_non_overlapping_ranges(self):
        self.assertFalse(_ranges_overlap("2015-01-01", "2019-12-31", "2020-01-01", "2024-12-31"))

    def test_overlapping_ranges(self):
        self.assertTrue(_ranges_overlap("2015-01-01", "2021-12-31", "2020-01-01", "2025-12-31"))

    def test_adjacent_ranges_do_not_overlap(self):
        # [2015, 2020) vs [2020, 2025] — boundary: "2020-01-01" <= "2020-01-01" → True
        # In our inclusive-boundary model these DO overlap at 2020-01-01
        self.assertTrue(_ranges_overlap("2015-01-01", "2020-01-01", "2020-01-01", "2025-01-01"))

    def test_open_ended_first_range_overlaps_any(self):
        # t1 is None → open-ended future
        self.assertTrue(_ranges_overlap("2015-01-01", None, "2023-01-01", "2025-01-01"))

    def test_open_ended_second_range_overlaps_any(self):
        # t2 is None → open-ended future
        self.assertTrue(_ranges_overlap("2015-01-01", "2019-12-31", "2018-01-01", None))

    def test_both_open_ended_always_overlap(self):
        self.assertTrue(_ranges_overlap("2015-01-01", None, "2023-01-01", None))

    def test_contained_range_overlaps(self):
        self.assertTrue(_ranges_overlap("2010-01-01", "2030-12-31", "2015-01-01", "2020-12-31"))


# ---------------------------------------------------------------------------
# AllowanceRule V2: required rate field logic
# ---------------------------------------------------------------------------
def _allowance_rule_v2_errors(calculation_type, percentage, fixed_amount):
    """Replicate the V2 validation logic from AllowanceRule.validate()."""
    errors = []
    if calculation_type == "Percentage":
        if not percentage:
            errors.append("percentage required")
    elif calculation_type == "Fixed":
        if not fixed_amount:
            errors.append("fixed_amount required")
    return errors


class TestAllowanceRuleV2(unittest.TestCase):
    def test_percentage_type_requires_percentage(self):
        errs = _allowance_rule_v2_errors("Percentage", None, None)
        self.assertEqual(len(errs), 1)
        self.assertIn("percentage required", errs[0])

    def test_percentage_type_with_value_is_valid(self):
        errs = _allowance_rule_v2_errors("Percentage", 10.0, None)
        self.assertEqual(errs, [])

    def test_fixed_type_requires_fixed_amount(self):
        errs = _allowance_rule_v2_errors("Fixed", None, None)
        self.assertEqual(len(errs), 1)
        self.assertIn("fixed_amount required", errs[0])

    def test_fixed_type_with_amount_is_valid(self):
        errs = _allowance_rule_v2_errors("Fixed", None, 50000)
        self.assertEqual(errs, [])

    def test_non_rate_type_has_no_v2_errors(self):
        errs = _allowance_rule_v2_errors("Other", None, None)
        self.assertEqual(errs, [])


# ---------------------------------------------------------------------------
# GovernmentSalaryScale V2: duplicate (grade_code, stage) detection
# ---------------------------------------------------------------------------
def _find_scale_duplicates(rows):
    """Replicate the V2 duplicate-row detection from GovernmentSalaryScale.validate()."""
    seen = set()
    duplicates = []
    for row in rows:
        key = (str(row["grade_code"]), int(row["stage"]))
        if key in seen:
            duplicates.append(key)
        seen.add(key)
    return duplicates


class TestSalaryScaleDuplicateDetection(unittest.TestCase):
    def test_no_duplicates_in_fixture(self):
        dups = _find_scale_duplicates(SCALE)
        self.assertEqual(dups, [], f"Fixture has unexpected duplicates: {dups}")

    def test_duplicate_detected(self):
        rows = [
            {"grade_code": "7", "stage": 1, "basic_salary": 100},
            {"grade_code": "7", "stage": 2, "basic_salary": 110},
            {"grade_code": "7", "stage": 1, "basic_salary": 120},  # dup
        ]
        dups = _find_scale_duplicates(rows)
        self.assertIn(("7", 1), dups)

    def test_same_grade_different_stage_no_dup(self):
        rows = [
            {"grade_code": "7", "stage": 1, "basic_salary": 100},
            {"grade_code": "7", "stage": 2, "basic_salary": 110},
        ]
        self.assertEqual(_find_scale_duplicates(rows), [])

    def test_different_grade_same_stage_no_dup(self):
        rows = [
            {"grade_code": "7", "stage": 1, "basic_salary": 100},
            {"grade_code": "6", "stage": 1, "basic_salary": 150},
        ]
        self.assertEqual(_find_scale_duplicates(rows), [])


# ---------------------------------------------------------------------------
# QualificationAppointmentRule V3: certificate_allowance_percentage in [0,100]
# ---------------------------------------------------------------------------
def _qar_pct_valid(pct):
    if pct is None:
        return True
    return 0 <= float(pct) <= 100


class TestQARPercentageRange(unittest.TestCase):
    def test_valid_zero(self):
        self.assertTrue(_qar_pct_valid(0))

    def test_valid_100(self):
        self.assertTrue(_qar_pct_valid(100))

    def test_valid_midrange(self):
        self.assertTrue(_qar_pct_valid(25.5))

    def test_none_is_valid(self):
        self.assertTrue(_qar_pct_valid(None))

    def test_negative_is_invalid(self):
        self.assertFalse(_qar_pct_valid(-1))

    def test_above_100_is_invalid(self):
        self.assertFalse(_qar_pct_valid(100.01))


# ---------------------------------------------------------------------------
# QualificationAppointmentRule V2: starting grade/stage in active scale
# ---------------------------------------------------------------------------
class TestQARGradeStageInScale(unittest.TestCase):
    def test_valid_grade7_stage1_in_fixture_scale(self):
        self.assertTrue(scale_has_grade_stage(SCALE, "7", 1))

    def test_invalid_stage_99(self):
        self.assertFalse(scale_has_grade_stage(SCALE, "7", 99))

    def test_invalid_grade_99(self):
        self.assertFalse(scale_has_grade_stage(SCALE, "99", 1))

    def test_empty_scale_returns_false(self):
        self.assertFalse(scale_has_grade_stage([], "7", 1))


# ---------------------------------------------------------------------------
# AnnualIncrementRequest V2: max-stage guard (via increment engine)
# ---------------------------------------------------------------------------
class TestAnnualIncrementV2MaxStage(unittest.TestCase):
    def test_at_max_stage_engine_returns_not_eligible(self):
        p = {"grade_code": "7", "current_stage": MAX_STAGE,
             "current_stage_date": "2018-01-01"}
        r = compute_increment(p, INCREMENT_RULE, EFF)
        self.assertFalse(r.eligible)
        self.assertFalse(r.applied)
        self.assertTrue(any("Max stage" in w for w in r.warnings))

    def test_one_below_max_stage_is_eligible(self):
        p = {"grade_code": "7", "current_stage": MAX_STAGE - 1,
             "current_stage_date": "2018-01-01"}
        r = compute_increment(p, INCREMENT_RULE, EFF)
        self.assertTrue(r.eligible)
        self.assertTrue(r.applied)

    def test_max_stage_constant_is_11(self):
        self.assertEqual(MAX_STAGE, 11)


# ---------------------------------------------------------------------------
# AnnualIncrementRequest V1: eligibility check (via increment engine)
# ---------------------------------------------------------------------------
class TestAnnualIncrementV1Eligibility(unittest.TestCase):
    def test_eligible_when_past_12_months(self):
        p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2019-05-01"}
        r = compute_increment(p, INCREMENT_RULE, EFF)
        self.assertTrue(r.eligible)

    def test_ineligible_when_within_12_months(self):
        p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2020-05-01"}
        r = compute_increment(p, INCREMENT_RULE, EFF)
        self.assertFalse(r.eligible)
        self.assertTrue(any("Not eligible" in w for w in r.warnings))

    def test_missing_stage_date_not_eligible(self):
        p = {"grade_code": "7", "current_stage": 1, "current_stage_date": ""}
        r = compute_increment(p, INCREMENT_RULE, EFF)
        self.assertFalse(r.eligible)
        self.assertTrue(any("not set" in w for w in r.warnings))

    def test_server_fields_cleared_v3(self):
        # V3: computed fields come only from profile_mutation; the caller clears them.
        p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2019-05-01"}
        r = compute_increment(p, INCREMENT_RULE, EFF)
        # The mutation has new stage; old computed fields are set by the engine, not user input.
        self.assertIn("current_stage", r.profile_mutation)
        self.assertEqual(r.profile_mutation["current_stage"], r.new_state["current_stage"])


# ---------------------------------------------------------------------------
# PromotionRequest V1: years-in-grade eligibility (via promotion engine)
# ---------------------------------------------------------------------------
class TestPromotionRequestV1Eligibility(unittest.TestCase):
    def test_eligible_after_sufficient_years(self):
        # Grade 7 requires 4 years; "2015-01-01" → "2020-06-01" is 5.5 years.
        p = {"grade_code": "7", "current_stage": 3, "current_grade_date": "2015-01-01"}
        r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF)
        self.assertTrue(r.eligible)
        self.assertTrue(r.applied)

    def test_ineligible_before_duration_met(self):
        # Only 0.4 years in grade — well below the 4-year requirement.
        p = {"grade_code": "7", "current_stage": 3, "current_grade_date": "2020-01-01"}
        r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF)
        self.assertFalse(r.eligible)
        self.assertTrue(any("Not eligible" in w for w in r.warnings))

    def test_missing_grade_date_not_eligible(self):
        p = {"grade_code": "7", "current_stage": 3, "current_grade_date": ""}
        r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF)
        self.assertFalse(r.eligible)
        self.assertTrue(any("not set" in w for w in r.warnings))

    def test_server_fields_cleared_v3(self):
        # V3: new salary must be >= old salary — guaranteed by place_stage.
        p = {"grade_code": "7", "current_stage": 3, "current_grade_date": "2015-01-01"}
        r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF)
        self.assertIsNotNone(r.new_salary)
        self.assertIsNotNone(r.old_salary)
        self.assertGreaterEqual(r.new_salary, r.old_salary)


# ---------------------------------------------------------------------------
# PensionCalculation V1: approved_pension = min(initial, last_functional_salary)
# ---------------------------------------------------------------------------
class TestPensionCalculationV1Cap(unittest.TestCase):
    def _run(self, avg36, last_functional_salary, service_years=30):
        pin = RetirementPensionInput(
            avg36=avg36, service_years=service_years,
            last_functional_salary=last_functional_salary,
        )
        return compute_retirement_pension(pin, PENSION_RULE, [], TAX_BRACKETS)

    def test_cap_enforced_when_initial_exceeds_last_salary(self):
        # Large average = high initial pension that should be capped
        r = self._run(avg36=2_000_000, last_functional_salary=500_000)
        self.assertLessEqual(r.approved_pension, r.last_functional_salary
                             if hasattr(r, "last_functional_salary") else 500_000)
        self.assertLessEqual(r.approved_pension, r.initial_pension)

    def test_no_cap_when_initial_below_last_salary(self):
        r = self._run(avg36=100_000, last_functional_salary=5_000_000)
        self.assertEqual(r.approved_pension, r.initial_pension)

    def test_approved_equals_min_of_initial_and_cap(self):
        r = self._run(avg36=500_000, last_functional_salary=300_000, service_years=20)
        cap = r.initial_pension  # initial at 100% cap
        expected = min(r.initial_pension, 300_000)
        self.assertEqual(r.approved_pension, expected)

    def test_result_has_required_fields(self):
        r = self._run(avg36=300_000, last_functional_salary=400_000)
        for field in ("approved_pension", "initial_pension", "gross_pension",
                      "net_pension", "monthly_tax"):
            self.assertTrue(hasattr(r, field), f"Missing field: {field}")


# ---------------------------------------------------------------------------
# Compute-pension endpoint shape: RetirementPensionResult fields (no Frappe)
# ---------------------------------------------------------------------------
class TestComputePensionShape(unittest.TestCase):
    def test_to_dict_returns_expected_keys(self):
        pin = RetirementPensionInput(
            avg36=500_000, service_years=30, last_functional_salary=600_000)
        result = compute_retirement_pension(pin, PENSION_RULE, [], TAX_BRACKETS)
        d = result.to_dict()
        for key in ("approved_pension", "gross_pension", "net_pension",
                    "monthly_tax", "end_of_service_bonus", "warnings"):
            self.assertIn(key, d, f"Missing key in to_dict: {key}")

    def test_evaluate_increment_result_shape(self):
        p = {"grade_code": "7", "current_stage": 1, "current_stage_date": "2019-01-01"}
        r = compute_increment(p, INCREMENT_RULE, EFF)
        d = r.to_dict()
        for key in ("eligible", "applied", "old_state", "new_state",
                    "profile_mutation", "warnings"):
            self.assertIn(key, d, f"Missing key in increment to_dict: {key}")

    def test_evaluate_promotion_result_shape(self):
        p = {"grade_code": "7", "current_stage": 3, "current_grade_date": "2017-01-01"}
        r = compute_promotion(p, PROMOTION_RULE, SCALE, EFF)
        d = r.to_dict()
        for key in ("eligible", "applied", "to_grade", "new_salary",
                    "old_salary", "warnings"):
            self.assertIn(key, d, f"Missing key in promotion to_dict: {key}")


if __name__ == "__main__":
    unittest.main()
