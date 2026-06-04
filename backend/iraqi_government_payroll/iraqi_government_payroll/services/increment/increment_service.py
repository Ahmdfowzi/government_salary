# Copyright (c) 2026, Iraqi Government Payroll
"""Annual Increment engine (M6) — pure Python, no Frappe.

Moves an employee one stage up within the same grade after the eligibility
period. Updates profile inputs only (current_stage, current_stage_date); the
Salary Slip recomputes pay from the updated profile later. Payroll/tax/pension
engines are unchanged.
"""

import calendar
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import List, Optional

from ..payroll_engine.types import PayrollError

INCREMENT_ENGINE_VERSION = "m6-increment-0.1.0"
MAX_STAGE = 11
DEFAULT_ELIGIBILITY_MONTHS = 12


def _to_date(value):
	if value in (None, ""):
		return None
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value)[:10])


def add_months(d, months):
	"""Return d advanced by `months` (clamping the day to the month length)."""
	total = d.month - 1 + int(months)
	y = d.year + total // 12
	m = total % 12 + 1
	day = min(d.day, calendar.monthrange(y, m)[1])
	return date(y, m, day)


@dataclass
class IncrementResult:
	eligible: bool
	applied: bool
	old_state: dict
	new_state: dict
	profile_mutation: dict
	effective_date: str
	rule_set: Optional[str]
	engine_version: str
	warnings: List[str] = field(default_factory=list)
	provisional_flags: List[str] = field(default_factory=list)

	def to_dict(self):
		return asdict(self)


def compute_increment(profile, rule, effective_date, rule_set=None):
	"""Compute an annual increment for a profile state.

	profile: dict with grade_code, current_stage, current_stage_date.
	rule: Annual Increment Rule dict (eligibility_months; default 12).
	Returns IncrementResult (never raises for eligibility — uses applied/warnings).
	"""
	elig_months = (rule or {}).get("eligibility_months") or DEFAULT_ELIGIBILITY_MONTHS
	gc = str(profile.get("grade_code"))
	stage = int(profile.get("current_stage"))
	csd = profile.get("current_stage_date")
	eff = _to_date(effective_date)

	old_state = {"grade_code": gc, "current_stage": stage, "current_stage_date":
				 str(csd) if csd else None}
	warnings, provisional = [], []

	def result(eligible, applied, new_state, mutation):
		return IncrementResult(
			eligible=eligible, applied=applied, old_state=old_state, new_state=new_state,
			profile_mutation=mutation, effective_date=str(effective_date), rule_set=rule_set,
			engine_version=INCREMENT_ENGINE_VERSION, warnings=warnings, provisional_flags=provisional)

	# Max stage: never auto-promote to a higher grade.
	if stage >= MAX_STAGE:
		warnings.append(f"Max stage ({MAX_STAGE}) reached — promotion required, no increment applied.")
		return result(eligible=False, applied=False, new_state=dict(old_state), mutation={})

	# Eligibility: current_stage_date + eligibility_months <= effective_date
	csd_date = _to_date(csd)
	if csd_date is None:
		warnings.append("current_stage_date not set — increment eligibility cannot be determined.")
		return result(eligible=False, applied=False, new_state=dict(old_state), mutation={})
	if eff < add_months(csd_date, elig_months):
		warnings.append(
			f"Not eligible: requires {elig_months} months since current stage date "
			f"({csd_date.isoformat()}).")
		return result(eligible=False, applied=False, new_state=dict(old_state), mutation={})

	new_stage = stage + 1
	new_state = {"grade_code": gc, "current_stage": new_stage, "current_stage_date": str(effective_date)}
	mutation = {"current_stage": new_stage, "current_stage_date": str(effective_date)}
	return result(eligible=True, applied=True, new_state=new_state, mutation=mutation)
