# Copyright (c) 2026, Iraqi Government Payroll
"""Salary Scale Resolver — basic salary lookup keyed on (rule_set, grade_code, stage).

grade_code is the canonical key:
  - Regular grades: "10" .. "1"
  - Senior grades : "SPECIAL_A", "SPECIAL_B", "SPECIAL_C"
"""

from .types import PayrollError


def resolve_grade_code(grade_code, current_grade=None):
	"""Return the canonical grade_code, falling back to current_grade only if empty.

	grade_code (Select on the profile) is authoritative and supports senior grades
	(SPECIAL_A/B/C). current_grade (legacy Int) is used only when grade_code is
	empty, and only represents regular grades.
	"""
	if grade_code not in (None, ""):
		return str(grade_code)
	if current_grade in (None, ""):
		raise PayrollError("Employee has neither grade_code nor current_grade set")
	return str(current_grade)


def get_active_scale(scales, rule_set_code):
	"""Return the active salary scale for a rule set (falls back to the only scale)."""
	cands = [s for s in scales if s.get("rule_set") == rule_set_code and s.get("is_active")]
	if not cands:
		cands = [s for s in scales if s.get("rule_set") == rule_set_code]
	if not cands:
		raise PayrollError(f"No salary scale found for rule set {rule_set_code}")
	if len(cands) > 1:
		raise PayrollError(f"Multiple active salary scales for rule set {rule_set_code}")
	return cands[0]


def get_basic_salary(scale_details, grade_code, stage):
	"""Return the stored basic salary for (grade_code, stage)."""
	gc = str(grade_code)
	st = int(stage)
	for d in scale_details:
		if str(d.get("grade_code")) == gc and int(d.get("stage")) == st:
			return d.get("basic_salary")
	raise PayrollError(f"No salary scale row for grade_code={gc} stage={st}")


def scale_has_grade_stage(scale_details, grade_code, stage):
	"""Pure predicate: does a (grade_code, stage) row exist in the scale? (M4.1)

	Used to validate employee placement before payroll calculation, without
	raising. Returns False on an empty/None stage so callers can skip cleanly.
	"""
	if grade_code in (None, "") or stage in (None, ""):
		return False
	gc = str(grade_code)
	try:
		st = int(stage)
	except (TypeError, ValueError):
		return False
	return any(str(d.get("grade_code")) == gc and int(d.get("stage")) == st
			   for d in scale_details or [])
