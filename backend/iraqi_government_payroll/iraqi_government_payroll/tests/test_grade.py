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


DOCTYPE_DIR = os.path.join(HERE, "..", "government_payroll", "doctype")


def doctype(name):
	"""Load a DocType JSON by snake_case folder name."""
	with open(os.path.join(DOCTYPE_DIR, name, name + ".json"), encoding="utf-8") as f:
		return json.load(f)


def field(dt, fieldname):
	for f in dt.get("fields", []):
		if f.get("fieldname") == fieldname:
			return f
	return None


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

	def test_master_rows_active_and_named(self):
		# M4.2: every fixture grade is active and carries an Arabic name
		for g in GRADE_MASTER:
			self.assertEqual(g.get("active"), 1, f"{g['name']} not active")
			self.assertTrue(g.get("grade_name_ar"), f"{g['name']} missing grade_name_ar")

	def test_master_schema_has_active_and_renamed_labels(self):
		dt = doctype("government_grade")
		self.assertEqual(field(dt, "active")["fieldtype"], "Check")
		self.assertIsNotNone(field(dt, "grade_name_ar"), "grade_name_ar field missing")
		self.assertIsNone(field(dt, "grade_label_ar"), "old grade_label_ar still present")


class TestGradeArchitecture(unittest.TestCase):
	"""M4.2: grade is a Link -> Government Grade everywhere; stage stays Int; no
	Government Stage DocType; Government Position owns neither grade nor stage."""

	def _assert_link(self, dt_name, fieldname):
		f = field(doctype(dt_name), fieldname)
		self.assertIsNotNone(f, f"{dt_name}.{fieldname} missing")
		self.assertEqual(f["fieldtype"], "Link", f"{dt_name}.{fieldname} not a Link")
		self.assertEqual(f["options"], "Government Grade",
						 f"{dt_name}.{fieldname} not linked to Government Grade")

	def test_grade_links_to_master(self):
		self._assert_link("government_employee_payroll_profile", "grade")
		self._assert_link("government_employee_payroll_profile", "appointment_grade_ref")
		self._assert_link("government_salary_scale_detail", "grade_ref")
		self._assert_link("qualification_appointment_rule", "starting_grade_ref")
		self._assert_link("promotion_request", "from_grade_ref")
		self._assert_link("promotion_request", "to_grade_ref")
		self._assert_link("annual_increment_request", "current_grade_ref")
		self._assert_link("promotion_grade_duration", "from_grade")
		self._assert_link("promotion_grade_duration", "to_grade")
		self._assert_link("employee_appointment", "grade_code")

	def test_stage_stays_int_no_stage_doctype(self):
		prof = doctype("government_employee_payroll_profile")
		for fn in ("current_stage", "appointment_stage"):
			self.assertEqual(field(prof, fn)["fieldtype"], "Int",
							 f"{fn} must stay Int (employee-level progression)")
		# there is NO Government Stage master DocType
		self.assertFalse(os.path.isdir(os.path.join(DOCTYPE_DIR, "government_stage")),
						 "Government Stage DocType must not exist")

	def test_deprecated_mirrors_hidden_and_readonly(self):
		"""M4.2 UI cleanup: legacy grade mirrors are hidden + read-only so users
		only ever interact with the Government Grade Link fields."""
		mirrors = {
			"government_employee_payroll_profile": ["grade_code", "current_grade", "appointment_grade"],
			"promotion_request": ["from_grade", "to_grade"],
			"annual_increment_request": ["current_grade"],
			"qualification_appointment_rule": ["starting_grade"],
		}
		for dt_name, fieldnames in mirrors.items():
			dt = doctype(dt_name)
			for fn in fieldnames:
				f = field(dt, fn)
				self.assertIsNotNone(f, f"{dt_name}.{fn} missing")
				self.assertEqual(f.get("hidden"), 1, f"{dt_name}.{fn} must be hidden")
				self.assertEqual(f.get("read_only"), 1, f"{dt_name}.{fn} must be read_only")

	def test_link_fields_visible_and_grade_required(self):
		"""The real Link fields stay visible; grade is the required authoritative input."""
		visible_links = {
			"government_employee_payroll_profile": ["grade", "appointment_grade_ref"],
			"government_salary_scale_detail": ["grade_ref"],
			"qualification_appointment_rule": ["starting_grade_ref"],
			"promotion_request": ["from_grade_ref", "to_grade_ref"],
			"annual_increment_request": ["current_grade_ref"],
		}
		for dt_name, fieldnames in visible_links.items():
			dt = doctype(dt_name)
			for fn in fieldnames:
				self.assertNotEqual(field(dt, fn).get("hidden"), 1,
									f"{dt_name}.{fn} (Link) must stay visible")
		grade = field(doctype("government_employee_payroll_profile"), "grade")
		self.assertEqual(grade.get("reqd"), 1, "profile.grade must be required")
		self.assertNotEqual(grade.get("hidden"), 1, "profile.grade must be visible")
		self.assertNotEqual(grade.get("read_only"), 1, "profile.grade must be editable")

	def test_position_owns_no_grade_or_stage(self):
		pos = doctype("government_position")
		for f in pos.get("fields", []):
			fn = (f.get("fieldname") or "").lower()
			self.assertNotIn("grade", fn, f"Position must not own grade field: {fn}")
			self.assertNotIn("stage", fn, f"Position must not own stage field: {fn}")
		# the old advisory grade_band is gone; position_type replaces it
		self.assertIsNone(field(pos, "grade_band"), "grade_band must be removed from Position")
		self.assertIsNotNone(field(pos, "position_type"), "position_type missing on Position")


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
