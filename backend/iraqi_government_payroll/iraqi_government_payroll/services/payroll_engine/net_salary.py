# Copyright (c) 2026, Iraqi Government Payroll
"""Net Salary Orchestrator (M5).

Combines the M3 active-salary engine with the M4 pension-deduction and tax
engines into a single monthly net salary. Pure Python (no Frappe). Engine
internals are unchanged; round_iqd is applied only at this Salary Slip boundary.

    basic + allowances = gross
    gross - pension_deduction - tax - other = net

Pension deduction does NOT reduce the tax base (per M4.5; revisit if confirmed).
confirmed=false behaviour and warnings from the underlying engines are preserved
and propagated; missing legal values are never invented.
"""

from dataclasses import dataclass, field, asdict
from typing import List

from .engine import calculate_active_salary
from .types import ENGINE_VERSION, AllowanceLine
from ..tax.tax_service import (
	compute_monthly_tax, resolve_legal_allowances, round_iqd, TAX_ENGINE_VERSION,
)
from ..pension.pension_service import compute_pension_deduction, PENSION_ENGINE_VERSION


def engine_versions():
	"""Composite engine-version structure stamped into the Salary Slip snapshot."""
	return {
		"active_salary_engine": ENGINE_VERSION,
		"tax_engine": TAX_ENGINE_VERSION,
		"pension_engine": PENSION_ENGINE_VERSION,
	}


@dataclass
class NetSalaryResult:
	rule_set: str
	engine_versions: dict
	period_date: str
	grade_code: str
	stage: int
	basic_salary: int
	capped_allowance_total: int
	non_capped_allowance_total: int
	gross_salary: int
	pension_deduction: int
	tax: int
	other_deductions: int
	total_deductions: int
	net_salary: int
	allowance_lines: List[AllowanceLine] = field(default_factory=list)
	warnings: List[str] = field(default_factory=list)
	provisional_flags: List[str] = field(default_factory=list)

	def to_dict(self):
		return asdict(self)


def _taxpayer_status(emp):
	return "Married" if getattr(emp, "spouse_eligible", False) else "Single"


def compute_net_salary(ctx, emp, other_deductions=0):
	"""Active salary -> pension deduction -> tax -> net. Returns NetSalaryResult."""
	active = calculate_active_salary(ctx, emp)
	rs = active.rule_set
	warnings = list(active.warnings)
	provisional = list(active.provisional_flags)

	# --- Pension deduction (M4) ---
	ded_rule = next((r for r in ctx.allowance_rules
					 if r.get("rule_set") == rs and r.get("component_code") == "DED_PENSION"), None)
	pd = compute_pension_deduction(active.basic_salary, ded_rule)
	warnings += pd["warnings"]
	if pd.get("provisional"):
		provisional.append("DED_PENSION")
	pension_deduction = pd["amount"]

	# --- Income tax (M4) — Art.12 allowances 0 while PC-7 pending ---
	tax_allow_rules = [r for r in (getattr(ctx, "tax_allowance_rules", []) or [])
					   if r.get("rule_set") == rs]
	legal, tax_warn, tax_prov = resolve_legal_allowances(
		tax_allow_rules, _taxpayer_status(emp), getattr(emp, "children_count", 0))
	warnings += tax_warn
	provisional += tax_prov
	brackets = [b for b in (getattr(ctx, "income_tax_brackets", []) or [])
				if b.get("rule_set") == rs]

	gross_r = round_iqd(active.gross_salary)
	tax_res = compute_monthly_tax(gross_r, brackets, legal_allowances=legal)
	tax = tax_res["monthly_tax"]
	if legal == 0 and tax_allow_rules:
		provisional.append("INCOME_TAX")   # computed on gross; allowances pending (PC-7)

	other_r = round_iqd(other_deductions or 0)
	total_ded = pension_deduction + tax + other_r
	net = gross_r - total_ded

	return NetSalaryResult(
		rule_set=rs,
		engine_versions=engine_versions(),
		period_date=active.period_date,
		grade_code=active.grade_code,
		stage=active.stage,
		basic_salary=round_iqd(active.basic_salary),
		capped_allowance_total=round_iqd(active.capped_allowance_total),
		non_capped_allowance_total=round_iqd(active.non_capped_allowance_total),
		gross_salary=gross_r,
		pension_deduction=pension_deduction,
		tax=tax,
		other_deductions=other_r,
		total_deductions=total_ded,
		net_salary=net,
		allowance_lines=active.allowance_lines,
		warnings=warnings,
		provisional_flags=provisional,
	)
