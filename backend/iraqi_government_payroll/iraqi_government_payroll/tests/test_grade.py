# Copyright (c) 2026, Iraqi Government Payroll
"""Phase 5 M4.1 — Government Grade normalization & scale-placement validation.

Pure tests (no Frappe bench): they exercise the placement predicate and the
grade resolution that back the profile controller's validate(), plus assert the
master/fixture data preserves the exact legacy grade codes so the salary engine
keeps resolving identically. Live behaviours (controller throw, backfill,
promotion-without-Position, locked snapshots, demo seed) are covered by the
bench smoke check `grade_validation`.

Run:  python3 -m unittest test_grade -v
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(HERE, "..", "fixtures")
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.payroll_engine.scale_resolver import (  # noqa: E402
	get_basic_salary, resolve_grade_code, scale_has_grade_stage,
)
from iraqi_government_payroll.services.payroll_engine.types import PayrollError  # noqa: E402


def fx(name):
	with open(os.path.join(FIX, name), encoding="utf-8") as f:
		return json.load(f)


SCALE_DETAILS = fx("government_salary_scale.json")[0]["details"]
GRADE_MASTER = fx("government_grade.json")

# The exact codes that MUST be preserved (legacy Select option set).
LEGACY_CODES = ["10", "9", "8", "7", "6", "5", "4", "3", "2", "1",
				"SPECIAL_A", "SPECIAL_B", "SPECIAL_C"]


class TestGradeMaster(unittest.TestCase):
	"""The Government Grade master preserves every legacy code value."""

	def test_master_has_all_legacy_codes(self):
		names = {g["name"] for g in GRADE_MASTER}
		for code in LEGACY_CODES:
			self.assertIn(code, names, f"grade master missing legacy code {code}")

	def test_master_count_and_no_extras(self):
		# exactly the 13 legacy codes, nothing renamed or dropped
		self.assertEqual(len(GRADE_MASTER), len(LEGACY_CODES))
		self.assertEqual({g["name"] for g in GRADE_MASTER}, set(LEGACY_CODES))

	def test_master_has_sort_order_and_type(self):
		for g in GRADE_MASTER:
			self.assertIn("sort_order", g)
			self.assertIn(g.get("grade_type"), ("Regular", "Senior"))

	def test_special_grades_are_senior(self):
		by_name = {g["name"]: g for g in GRADE_MASTER}
		for code in ("SPECIAL_A", "SPECIAL_B", "SPECIAL_C"):
			self.assertEqual(by_name[code]["grade_type"], "Senior")


class TestScaleNormalization(unittest.TestCase):
	"""Salary Scale Detail carries a grade_ref Link mirroring grade_code exactly,
	and every grade_ref resolves to a master row — so the legal source of valid
	(grade, stage, basic) is unchanged."""

	def test_every_detail_has_grade_ref_equal_to_grade_code(self):
		for d in SCALE_DETAILS:
			self.assertEqual(str(d["grade_ref"]), str(d["grade_code"]))

	def test_every_grade_ref_exists_in_master(self):
		names = {g["name"] for g in GRADE_MASTER}
		for d in SCALE_DETAILS:
			self.assertIn(d["grade_ref"], names)

	def test_engine_resolution_unchanged_by_normalization(self):
		# get_basic_salary still keys on grade_code (string), unaffected by grade_ref
		self.assertEqual(get_basic_salary(SCALE_DETAILS, "1", 1), 910000)
		self.assertEqual(get_basic_salary(SCALE_DETAILS, 1, 1), 910000)


class TestPlacementPredicate(unittest.TestCase):
	"""scale_has_grade_stage backs the profile controller's V2 validation."""

	def test_valid_placement(self):
		self.assertTrue(scale_has_grade_stage(SCALE_DETAILS, "7", 1))
		self.assertTrue(scale_has_grade_stage(SCALE_DETAILS, 7, 1))   # int grade ok

	def test_invalid_stage_rejected(self):
		# grade 7 exists, stage 99 does not -> would block before payroll calc
		self.assertFalse(scale_has_grade_stage(SCALE_DETAILS, "7", 99))

	def test_unknown_grade_rejected(self):
		self.assertFalse(scale_has_grade_stage(SCALE_DETAILS, "NOPE", 1))

	def test_special_grade_placement(self):
		# senior grades participate in the same predicate if present in the scale
		has_special = any(str(d["grade_code"]) == "SPECIAL_A" for d in SCALE_DETAILS)
		if has_special:
			self.assertTrue(scale_has_grade_stage(SCALE_DETAILS, "SPECIAL_A", 1))

	def test_empty_inputs_return_false_not_raise(self):
		self.assertFalse(scale_has_grade_stage(SCALE_DETAILS, None, 1))
		self.assertFalse(scale_has_grade_stage(SCALE_DETAILS, "7", None))
		self.assertFalse(scale_has_grade_stage(SCALE_DETAILS, "7", ""))
		self.assertFalse(scale_has_grade_stage([], "7", 1))


class TestGradeResolution(unittest.TestCase):
	"""resolve_grade_code keeps the engine keyed on the same string value whether
	the source is the new grade Link, the deprecated grade_code, or legacy Int."""

	def test_link_value_preferred(self):
		# profile.grade (Link) == grade_code string -> identical engine key
		self.assertEqual(resolve_grade_code("SPECIAL_A", None), "SPECIAL_A")

	def test_fallback_to_legacy_int(self):
		self.assertEqual(resolve_grade_code(None, 7), "7")
		self.assertEqual(resolve_grade_code("", 7), "7")

	def test_raises_when_nothing_set(self):
		with self.assertRaises(PayrollError):
			resolve_grade_code(None, None)


if __name__ == "__main__":
	unittest.main()
