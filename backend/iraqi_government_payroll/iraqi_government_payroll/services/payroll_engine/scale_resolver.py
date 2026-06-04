# Copyright (c) 2026, Iraqi Government Payroll
"""Salary Scale Resolver — basic salary lookup keyed on (rule_set, grade_code, stage).

grade_code is the canonical key:
  - Regular grades: "10" .. "1"
  - Senior grades : "SPECIAL_A", "SPECIAL_B", "SPECIAL_C"
"""

from .types import PayrollError


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
