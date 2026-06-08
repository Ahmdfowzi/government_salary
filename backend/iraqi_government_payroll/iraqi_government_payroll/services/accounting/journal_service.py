# Copyright (c) 2026, Iraqi Government Payroll
"""Payroll accounting journal builder — PURE, proposal-only (Phase 4 M15).

Turns the per-employee payroll figures the reports already produced (basic,
earnings, deductions, net + component lines) into **balanced** double-entry
journal rows, using an explicit component→account mapping. It does NOT post to any
ledger and never creates GL Entry / Journal Entry documents — it only proposes
rows for export.

No payroll amounts are computed here; figures are read and summed only.

Balance (holds by construction):
  debits  = salary_expense + allowance_expense = Σ basic + Σ (earnings − basic) = Σ earnings
  credits = employee_payable + pension + tax + other = Σ net + Σ deductions      = Σ earnings
"""

DED_PENSION = "DED_PENSION"
INCOME_TAX = "INCOME_TAX"
DEDUCTION = "Deduction"


class JournalMappingError(Exception):
	"""Raised when the account mapping is missing an account that a non-zero
	amount requires. Carries the list of missing mapping keys."""

	def __init__(self, missing):
		self.missing = list(missing)
		super().__init__("Missing account mapping for: " + ", ".join(self.missing))


class JournalImbalanceError(Exception):
	"""Raised if debits != credits (a data-integrity safety net)."""


def _i(v):
	return int(v or 0)


def build_journal(rows, mapping):
	"""Return a balanced journal proposal from normalized payroll `rows`.

	`mapping` is a dict of account codes keyed by:
	  salary_expense_account, allowance_expense_account, employee_payable_account,
	  pension_payable_account, tax_payable_account, other_deductions_payable_account.

	Raises JournalMappingError if a non-zero amount has no mapped account.
	An empty run (no rows / all zeros) returns a safe, balanced, empty journal.
	"""
	salary = sum(_i(r.get("basic")) for r in rows)
	allowances = sum(_i(r.get("total_earnings")) - _i(r.get("basic")) for r in rows)
	net = sum(_i(r.get("net")) for r in rows)
	total_deductions = sum(_i(r.get("total_deductions")) for r in rows)

	pension = 0
	tax = 0
	for r in rows:
		for line in r.get("lines") or []:
			if line.get("line_type") != DEDUCTION:
				continue
			code = line.get("component_code")
			if code == DED_PENSION:
				pension += _i(line.get("amount"))
			elif code == INCOME_TAX:
				tax += _i(line.get("amount"))
	other = total_deductions - pension - tax

	# (amount, side, mapping key, description) — order = debits then credits.
	plan = [
		(salary, "debit", "salary_expense_account", "Salary Expense"),
		(allowances, "debit", "allowance_expense_account", "Allowance Expense"),
		(net, "credit", "employee_payable_account", "Employee Payable"),
		(pension, "credit", "pension_payable_account", "Pension Payable"),
		(tax, "credit", "tax_payable_account", "Tax Payable"),
		(other, "credit", "other_deductions_payable_account", "Other Deductions Payable"),
	]

	missing = [key for amount, _side, key, _desc in plan
			   if amount and not (mapping or {}).get(key)]
	if missing:
		raise JournalMappingError(missing)

	journal = []
	for amount, side, key, desc in plan:
		if not amount:
			continue
		journal.append({
			"account": mapping[key],
			"description": desc,
			"debit": amount if side == "debit" else 0,
			"credit": amount if side == "credit" else 0,
		})

	total_debit = sum(j["debit"] for j in journal)
	total_credit = sum(j["credit"] for j in journal)
	if total_debit != total_credit:
		raise JournalImbalanceError(
			f"debits {total_debit} != credits {total_credit}")

	return {
		"rows": journal,
		"total_debit": total_debit,
		"total_credit": total_credit,
		"balanced": True,
		"summary": {
			"salary_expense": salary, "allowance_expense": allowances,
			"employee_payable": net, "pension_payable": pension,
			"tax_payable": tax, "other_deductions_payable": other,
		},
	}
