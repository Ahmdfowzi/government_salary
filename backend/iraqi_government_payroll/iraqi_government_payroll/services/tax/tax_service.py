# Copyright (c) 2026, Iraqi Government Payroll
"""Income Tax service — progressive brackets (Law 113/1982, Article 13).

Phase 1: signatures only. Brackets and legal allowances are loaded as data in
Phase 2 (not hardcoded here).
"""


def compute_annual_tax(taxable_annual_income):
	"""Apply progressive brackets to taxable annual income -> annual tax."""
	raise NotImplementedError("Phase 2: implement progressive bracket tax.")


def compute_monthly_tax(monthly_gross, legal_allowances=0):
	"""Annualize, deduct legal allowances, bracket, divide by 12."""
	raise NotImplementedError("Phase 2: implement monthly tax.")
