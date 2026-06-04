# Copyright (c) 2026, Iraqi Government Payroll
"""Promotion engine (M6) — pure Python, no Frappe.

Moves an employee to the next higher grade after the grade-duration period, and
places them on a stage of the new grade per the post-promotion stage rule. Only
the salary scale is used (for stage placement) — full pay is NOT recomputed here;
the Salary Slip recomputes from the updated profile later. Updates profile inputs
only. Payroll/tax/pension engines are unchanged.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional

from ..payroll_engine.types import PayrollError
from ..payroll_engine.scale_resolver import get_basic_salary
from ..increment.increment_service import _to_date, add_months

PROMOTION_ENGINE_VERSION = "m6-promotion-0.1.0"
SENIOR_GRADES = {"SPECIAL_A", "SPECIAL_B", "SPECIAL_C"}


def place_stage(new_grade_details, old_salary):
	"""Post-promotion stage placement on the new grade.

	  * equal salary stage           -> that stage
	  * old salary between two stages -> next higher stage
	  * old salary below first stage  -> stage 1
	  * old salary above all stages   -> last stage
	"""
	rows = sorted(new_grade_details, key=lambda d: int(d.get("stage")))
	equal = [d for d in rows if d.get("basic_salary") == old_salary]
	if equal:
		return int(equal[0]["stage"])
	higher = [d for d in rows if d.get("basic_salary") > old_salary]
	if higher:
		return int(min(higher, key=lambda d: int(d["stage"]))["stage"])
	return int(rows[-1]["stage"])


@dataclass
class PromotionResult:
	eligible: bool
	applied: bool
	old_state: dict
	new_state: dict
	profile_mutation: dict
	to_grade: Optional[str]
	old_salary: Optional[int]
	new_salary: Optional[int]
	new_stage: Optional[int]
	effective_date: str
	rule_set: Optional[str]
	engine_version: str
	warnings: List[str] = field(default_factory=list)
	provisional_flags: List[str] = field(default_factory=list)

	def to_dict(self):
		return asdict(self)


def _find_duration(promotion_rule, grade_code):
	for d in (promotion_rule or {}).get("durations", []) or []:
		if str(d.get("from_grade")) == str(grade_code):
			return d
	return None


def compute_promotion(profile, promotion_rule, scale_details, effective_date, rule_set=None):
	"""Compute a promotion for a profile state. Uses grade_code as the canonical key.

	Raises PayrollError when a regular grade has no promotion duration rule.
	Senior grades return not-applied (no auto-promote) unless an explicit rule exists.
	"""
	gc = str(profile.get("grade_code"))
	stage = int(profile.get("current_stage"))
	cgd = profile.get("current_grade_date")
	eff = _to_date(effective_date)

	old_state = {"grade_code": gc, "current_stage": stage,
				 "current_grade_date": str(cgd) if cgd else None}
	warnings, provisional = [], []

	def result(eligible, applied, new_state, mutation, to_grade=None,
			   old_salary=None, new_salary=None, new_stage=None):
		return PromotionResult(
			eligible=eligible, applied=applied, old_state=old_state, new_state=new_state,
			profile_mutation=mutation, to_grade=to_grade, old_salary=old_salary,
			new_salary=new_salary, new_stage=new_stage, effective_date=str(effective_date),
			rule_set=rule_set, engine_version=PROMOTION_ENGINE_VERSION,
			warnings=warnings, provisional_flags=provisional)

	dur = _find_duration(promotion_rule, gc)
	if dur is None:
		if gc in SENIOR_GRADES:
			warnings.append("Senior grade does not auto-promote without an explicit promotion rule.")
			return result(eligible=False, applied=False, new_state=dict(old_state), mutation={})
		raise PayrollError(f"No promotion duration rule for grade {gc}.")

	to_grade = str(dur.get("to_grade"))
	years = int(dur.get("years"))

	cgd_date = _to_date(cgd)
	if cgd_date is None:
		warnings.append("current_grade_date not set — promotion eligibility cannot be determined.")
		return result(eligible=False, applied=False, new_state=dict(old_state), mutation={})
	if eff < add_months(cgd_date, years * 12):
		warnings.append(f"Not eligible: requires {years} years in grade {gc} "
						f"(since {cgd_date.isoformat()}).")
		return result(eligible=False, applied=False, new_state=dict(old_state), mutation={})

	old_salary = get_basic_salary(scale_details, gc, stage)
	new_details = [d for d in scale_details if str(d.get("grade_code")) == to_grade]
	if not new_details:
		raise PayrollError(f"No salary scale rows for grade {to_grade}.")
	new_stage = place_stage(new_details, old_salary)
	new_salary = get_basic_salary(scale_details, to_grade, new_stage)

	new_state = {
		"grade_code": to_grade,
		"current_grade": int(to_grade) if to_grade.isdigit() else 0,
		"current_stage": new_stage,
		"current_grade_date": str(effective_date),
		"current_stage_date": str(effective_date),
	}
	mutation = dict(new_state)
	return result(eligible=True, applied=True, new_state=new_state, mutation=mutation,
				  to_grade=to_grade, old_salary=old_salary, new_salary=new_salary, new_stage=new_stage)
