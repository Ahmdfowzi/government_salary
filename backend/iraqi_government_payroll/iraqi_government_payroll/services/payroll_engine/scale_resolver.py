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


def resolve_basic_salary(rule_set, grade, current_stage, grade_ref=None, current_grade=None):
	"""Frappe-backed resolver: look up basic_salary from the active salary scale.

	Intended for profile validate / before_save. Returns 0.0 (and logs) on any
	lookup failure instead of raising, so save is never blocked by a missing scale.

	Grade precedence: grade_ref (Link) > grade (str/code) > current_grade (Int legacy).
	Scale precedence: is_active=1 first; falls back to any scale for the rule set.

	Supports:
	  - grade_ref Link field (same value as grade_code, preferred)
	  - grade_code text field fallback
	  - numeric current_grade fallback for legacy records
	  - stage / current_stage normalised to int
	  - active scale only (with fallback to sole scale when none marked active)
	"""
	import frappe

	# 1. Resolve canonical grade string: grade_ref (Link) > grade (str) > current_grade (Int)
	raw = grade_ref or grade or (str(current_grade) if current_grade not in (None, "") else "")
	gc = str(raw).strip() if raw else ""
	if not gc:
		frappe.log_error("resolve_basic_salary: profile has no grade set", "Payroll Salary Resolution")
		return 0.0

	# 2. Normalise stage to int
	try:
		st = int(current_stage)
	except (TypeError, ValueError):
		frappe.log_error(
			f"resolve_basic_salary: invalid stage value '{current_stage}' for grade '{gc}'",
			"Payroll Salary Resolution",
		)
		return 0.0

	if not rule_set:
		return 0.0

	# 3. Find active scale; fall back to any scale for the rule set when none is marked active
	scale = (
		frappe.db.get_value("Government Salary Scale", {"rule_set": rule_set, "is_active": 1}, "name")
		or frappe.db.get_value("Government Salary Scale", {"rule_set": rule_set}, "name")
	)
	if not scale:
		frappe.log_error(
			f"resolve_basic_salary: no salary scale for rule_set='{rule_set}'",
			"Payroll Salary Resolution",
		)
		return 0.0

	# 4. Fetch scale detail rows; match on grade_ref (Link) first, then grade_code (string)
	details = frappe.get_all(
		"Government Salary Scale Detail",
		filters={"parent": scale},
		fields=["grade_code", "grade_ref", "stage", "basic_salary"],
	)

	for d in details:
		d_gc = str(d.get("grade_ref") or d.get("grade_code") or "")
		try:
			d_st = int(d.get("stage") or 0)
		except (TypeError, ValueError):
			continue
		if d_gc == gc and d_st == st:
			return float(d.get("basic_salary") or 0)

	frappe.log_error(
		f"resolve_basic_salary: no detail row for grade='{gc}' stage={st} in scale '{scale}'",
		"Payroll Salary Resolution",
	)
	return 0.0
