# Copyright (c) 2026, Iraqi Government Payroll
"""Payroll Engine — Core Active Salary orchestrator (M3).

Pure-Python, backend-only, no Frappe dependency in the math path (so it is unit
testable against the fixtures directly). Production wiring that loads data from
Frappe lives in ``repository.py``.

GOLDEN RULES:
  * Rule set is chosen by the payroll period date.
  * Every percentage is computed on BASIC salary only.
  * No figure is calculated in the frontend.

M3 scope: basic salary + active allowances + 200% cap -> gross.
NOT in M3: income tax, pension deduction, retirement pension, increment,
promotion, payroll run, salary slip.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .types import CalculationResult, ENGINE_VERSION
from .rule_resolver import resolve_rule_set
from .scale_resolver import get_active_scale, get_basic_salary
from ..allowance.allowance_service import resolve_active_allowances, apply_200_cap


@dataclass
class EmployeeInput:
	grade_code: str
	stage: int
	period_date: str
	qualification: Optional[str] = None
	position_allowance_category: Optional[str] = None
	risk_applicable: bool = False
	risk_category: Optional[str] = None
	spouse_eligible: bool = False
	children_count: int = 0


@dataclass
class DataContext:
	rule_sets: List[dict]
	scales: List[dict]
	allowance_rules: List[dict]
	income_tax_brackets: List[dict] = field(default_factory=list)
	tax_allowance_rules: List[dict] = field(default_factory=list)


def calculate_active_salary(ctx: "DataContext", emp: "EmployeeInput") -> CalculationResult:
	"""Compute the active monthly salary for one employee input against a data context."""
	rule_set = resolve_rule_set(ctx.rule_sets, emp.period_date)
	rs_code = rule_set.get("name") or rule_set.get("rule_set_code")

	scale = get_active_scale(ctx.scales, rs_code)
	basic = get_basic_salary(scale.get("details", []), emp.grade_code, emp.stage)

	rules = [r for r in ctx.allowance_rules
			 if r.get("rule_set") == rs_code and r.get("is_active")]

	lines, warnings, provisional = resolve_active_allowances(rules, emp, basic)
	capped_total, non_capped_total, excluded, cap_warnings = apply_200_cap(lines, basic)
	warnings = warnings + cap_warnings

	gross = round(basic + capped_total + non_capped_total, 2)

	return CalculationResult(
		rule_set=rs_code,
		engine_version=ENGINE_VERSION,
		period_date=str(emp.period_date),
		grade_code=str(emp.grade_code),
		stage=int(emp.stage),
		basic_salary=basic,
		allowance_lines=lines,
		capped_allowance_total=capped_total,
		non_capped_allowance_total=non_capped_total,
		cap_excluded_amount=excluded,
		gross_salary=gross,
		warnings=warnings,
		provisional_flags=provisional,
	)
