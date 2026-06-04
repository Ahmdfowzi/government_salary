# Copyright (c) 2026, Iraqi Government Payroll
"""Pension engine — active pension deduction + retirement pension (Article 21).

Pure functions (no Frappe). Honors the M3 confirmed=false contract and never
invents missing legal values. Money is rounded half-up to integer dinar.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional

from ..tax.tax_service import compute_monthly_tax, round_iqd

PENSION_ENGINE_VERSION = "m4-pension-0.1.0"


# --------------------------------------------------------------------------- #
# 1) Active-salary pension deduction (contribution)                           #
# --------------------------------------------------------------------------- #
def compute_pension_deduction(basic_salary, contribution_rate_rule):
	"""Compute the active-salary pension contribution deduction.

	contribution_rate_rule is the DED_PENSION Allowance Rule dict (or None).
	  - confirmed=false & empty  -> 0 + warning (skipped)   [PC-6 pending]
	  - confirmed=false & value  -> compute + provisional flag
	  - confirmed=true  & value  -> compute normally
	Does not affect the tax base (kept independent until explicitly configured).
	"""
	warnings, provisional = [], []
	if contribution_rate_rule is None:
		return {"amount": 0, "rate": None, "skipped": True, "provisional": False,
				"warnings": ["No pension contribution rule configured — deduction omitted."]}

	rate = contribution_rate_rule.get("percentage")
	confirmed = bool(contribution_rate_rule.get("confirmed"))
	code = contribution_rate_rule.get("component_code", "DED_PENSION")

	if rate in (None, ""):
		msg = (f"{code}: pension contribution rate not set (PC-6) — deduction omitted."
			   if not confirmed else f"{code}: no rate configured — deduction omitted.")
		return {"amount": 0, "rate": None, "skipped": True, "provisional": False,
				"warnings": [msg]}

	amount = round_iqd(float(basic_salary) * float(rate) / 100.0)
	if not confirmed:
		provisional.append(code)
	return {"amount": amount, "rate": float(rate), "skipped": False,
			"provisional": bool(provisional), "warnings": warnings}


# --------------------------------------------------------------------------- #
# 2) Retirement pension (Article 21)                                          #
# --------------------------------------------------------------------------- #
@dataclass
class RetirementPensionInput:
	avg36: float                       # average of last 36 functional salaries
	service_years: int
	last_functional_salary: float      # 100% cap base (without allowances)
	extra_months: int = 0
	last_full_salary: float = 0.0      # EOS base (with allowances)
	qualification: Optional[str] = None
	# Cost-of-living override (used for tests / when configured on the rule):
	cost_of_living_method: Optional[str] = None
	cost_of_living_value: Optional[float] = None
	other_deductions: float = 0.0
	legal_allowances: float = 0.0      # annual Art.12 (0 while PC-7 pending)
	period_date: Optional[str] = None
	rule_set: Optional[str] = None


@dataclass
class RetirementPensionResult:
	rule_set: Optional[str]
	engine_version: str
	period_date: Optional[str]
	avg36: float
	service_months: int
	initial_pension: float
	approved_pension: float
	certificate_allowance: float
	cost_of_living: float
	gross_pension: float
	taxable_income: float
	legal_allowances: float
	annual_tax: float
	monthly_tax: float
	other_deductions: float
	net_pension: float
	end_of_service_bonus: float
	warnings: List[str] = field(default_factory=list)
	provisional_flags: List[str] = field(default_factory=list)

	def to_dict(self):
		return asdict(self)


def _find_certificate_rate(certificate_rules, qualification):
	for r in certificate_rules or []:
		if r.get("match_key") == "Pension Certificate" and r.get("match_value") == qualification:
			return r
	return None


def _cost_of_living(method, value, approved, service_years, default_minimum, warnings):
	if not method:
		warnings.append("Cost-of-living method not set (PC-9) — cost of living = 0.")
		return 0
	if value in (None, "") and method != "Minimum Top-up":
		warnings.append(f"Cost-of-living method '{method}' has no value — cost of living = 0.")
		return 0
	if method == "Fixed Percentage":
		return round_iqd(approved * float(value) / 100.0)
	if method == "Per Year Percentage":
		return round_iqd(approved * float(value) / 100.0 * service_years)
	if method == "Minimum Top-up":
		floor = float(default_minimum or 0)
		return round_iqd(max(0.0, floor - approved))
	if method == "Manual":
		return round_iqd(float(value or 0))
	warnings.append(f"Unknown cost-of-living method '{method}' — cost of living = 0.")
	return 0


def compute_retirement_pension(pension_input, pension_rule, certificate_rules, tax_brackets):
	"""Compute the Article-21 retirement pension. Pure; returns RetirementPensionResult."""
	warnings, provisional = [], []
	i = pension_input

	accrual = float(pension_rule.get("accrual_rate") or 0)            # e.g. 2.5
	cap_pct = float(pension_rule.get("cap_pct_of_last_salary") or 100)
	eos_min = int(pension_rule.get("eos_min_service_years") or 30)
	default_min = pension_rule.get("default_minimum_pension")

	service_months = int(i.service_years) * 12 + int(i.extra_months or 0)

	initial = round_iqd(float(i.avg36) * (accrual / 100.0) * service_months / 12.0)
	cap_amount = round_iqd(float(i.last_functional_salary) * cap_pct / 100.0)
	approved = min(initial, cap_amount)

	# Certificate pension allowance on the approved pension
	cert_rule = _find_certificate_rate(certificate_rules, i.qualification)
	if cert_rule is None or cert_rule.get("percentage") in (None, ""):
		certificate = 0
		warnings.append(
			f"No pension certificate allowance for qualification '{i.qualification}' — allowance = 0.")
	else:
		certificate = round_iqd(approved * float(cert_rule.get("percentage")) / 100.0)
		if not bool(cert_rule.get("confirmed")):
			provisional.append(cert_rule.get("component_code", "CERT_PEN"))

	# Cost of living: input override first, else from the pension rule
	col_method = i.cost_of_living_method or pension_rule.get("cost_of_living_method")
	col_value = i.cost_of_living_value if i.cost_of_living_value is not None \
		else pension_rule.get("cost_of_living_value")
	cost_of_living = _cost_of_living(col_method, col_value, approved, int(i.service_years),
									default_min, warnings)

	gross = approved + certificate + cost_of_living

	# Tax on the (annualized) gross pension — Art.12 allowances 0 while PC-7 pending
	tax = compute_monthly_tax(gross, tax_brackets, legal_allowances=i.legal_allowances or 0)
	if not (i.legal_allowances or 0):
		warnings.append("Pension tax computed without Art.12 legal allowances (PC-7 pending).")

	net = gross - tax["monthly_tax"] - round_iqd(i.other_deductions or 0)

	eos = round_iqd(float(i.last_full_salary) * 12.0) if int(i.service_years) >= eos_min else 0
	if int(i.service_years) >= eos_min and not i.last_full_salary:
		warnings.append("End-of-service bonus due but last_full_salary is 0.")

	return RetirementPensionResult(
		rule_set=i.rule_set,
		engine_version=PENSION_ENGINE_VERSION,
		period_date=i.period_date,
		avg36=round_iqd(i.avg36),
		service_months=service_months,
		initial_pension=initial,
		approved_pension=approved,
		certificate_allowance=certificate,
		cost_of_living=cost_of_living,
		gross_pension=gross,
		taxable_income=tax["taxable_annual"],
		legal_allowances=tax["legal_allowances"],
		annual_tax=tax["annual_tax"],
		monthly_tax=tax["monthly_tax"],
		other_deductions=round_iqd(i.other_deductions or 0),
		net_pension=net,
		end_of_service_bonus=eos,
		warnings=warnings,
		provisional_flags=provisional,
	)
