# Copyright (c) 2026, Iraqi Government Payroll
"""Income Tax engine — progressive brackets (Law 113/1982, Article 13).

Pure functions (no Frappe). Tax is computed ONLY from Income Tax Bracket data.
Brackets are annual; monthly tax = round-half-up(annual_tax / 12). Taxable income
cannot go below 0. Legal allowances (Art. 12) are resolved separately and are 0
while PC-7/8 are pending (with a warning) — never invented.
"""

from decimal import Decimal, ROUND_HALF_UP

TAX_ENGINE_VERSION = "m4-tax-0.1.0"


def round_iqd(value):
	"""Round to the nearest integer dinar, half-up."""
	return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _sorted_brackets(brackets):
	def key(b):
		if b.get("seq") is not None:
			return b.get("seq")
		return float(b.get("from_amount") or 0)
	return sorted(brackets, key=key)


def compute_annual_tax(taxable_annual, brackets):
	"""Apply progressive brackets to an annual taxable amount. Returns integer dinar."""
	taxable = max(0.0, float(taxable_annual or 0))
	tax = 0.0
	for b in _sorted_brackets(brackets):
		lo = float(b.get("from_amount") or 0)
		hi = b.get("to_amount")
		hi = float(hi) if hi not in (None, "") else None
		rate = float(b.get("rate") or 0) / 100.0
		if taxable <= lo:
			continue
		upper = taxable if hi is None else min(taxable, hi)
		portion = max(0.0, upper - lo)
		tax += portion * rate
	return round_iqd(tax)


def compute_monthly_tax(monthly_gross, brackets, legal_allowances=0, exemptions=0):
	"""Annualize gross, deduct allowances/exemptions, bracket, divide by 12.

	Returns a dict: annual_gross, legal_allowances, exemptions, taxable_annual,
	annual_tax, monthly_tax.
	"""
	annual_gross = float(monthly_gross or 0) * 12.0
	taxable = max(0.0, annual_gross - float(legal_allowances or 0) - float(exemptions or 0))
	annual_tax = compute_annual_tax(taxable, brackets)
	return {
		"annual_gross": round_iqd(annual_gross),
		"legal_allowances": round_iqd(legal_allowances or 0),
		"exemptions": round_iqd(exemptions or 0),
		"taxable_annual": round_iqd(taxable),
		"annual_tax": annual_tax,
		"monthly_tax": round_iqd(annual_tax / 12.0),
	}


def resolve_legal_allowances(tax_allowance_rules, taxpayer_status=None, dependents=0):
	"""Resolve Art.12 legal allowances from Tax Allowance Rule rows.

	Honors the confirmed=false contract: provisional rows with a value are summed
	and flagged; empty rows are skipped with a warning. Returns
	(total_annual, warnings, provisional_flags). While PC-7/8 are pending all rows
	are empty -> total 0 with a warning (taxable falls back to gross).
	"""
	total = 0.0
	warnings, provisional = [], []
	applied_any = False
	for r in tax_allowance_rules or []:
		amount = r.get("annual_amount")
		confirmed = bool(r.get("confirmed"))
		name = r.get("name") or r.get("taxpayer_status")
		if amount in (None, ""):
			warnings.append(f"{name}: tax allowance value not set (PC-7/8 pending) — skipped.")
			continue
		total += float(amount)
		applied_any = True
		if not confirmed:
			provisional.append(name)
	if not applied_any:
		warnings.append("No confirmed Art.12 legal allowances — taxable income = gross (provisional).")
	return round_iqd(total), warnings, provisional
