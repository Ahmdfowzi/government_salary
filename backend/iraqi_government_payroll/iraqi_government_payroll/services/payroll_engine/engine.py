# Copyright (c) 2026, Iraqi Government Payroll
"""Payroll Engine — orchestrator for the active monthly salary calculation.

Pure-Python, backend-only. Coordinates the domain services (scale lookup,
allowance, tax, pension deduction, audit) following the documented order:

    resolve_law -> get_basic -> percentage_allowances -> apply_200_cap
    -> non_capped_allowances -> protected_difference/overtime -> gross
    -> tax + pension_deduction + other_deductions -> net -> audit log

GOLDEN RULES (Phase 2 implementation):
  * The salary law is chosen by the PAYROLL PERIOD DATE.
  * Every percentage is computed on BASIC salary only, never on gross.
  * No figure is calculated in the frontend.

Phase 1: signatures only. No business rules implemented.
"""


def calculate_active_salary(profile_name, period_date):
	"""Return a structured result for one employee's monthly salary.

	Args:
		profile_name: Government Employee Payroll Profile id.
		period_date: date used to resolve the applicable salary law.

	Returns: dict with basic, capped allowances, non-capped allowances,
	deductions, gross, net and an explained line breakdown.
	"""
	raise NotImplementedError("Phase 2: implement active salary calculation.")
