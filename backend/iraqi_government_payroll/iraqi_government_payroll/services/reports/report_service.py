# Copyright (c) 2026, Iraqi Government Payroll
"""Pure read-only payroll report aggregations (no Frappe).

Reports consume already-computed Salary Slip / Snapshot figures and only filter,
group and sum them — NO salary / tax / pension is ever recomputed here. The Frappe
wiring (fetching rows, and choosing live Slip vs immutable Snapshot by run state)
lives in api/reports_api.py.

A *normalized row* (built by the API layer from a Salary Slip or a Snapshot) is:

    {
      "employee_profile": str, "employee_name": str,
      "grade_code": str, "stage": int,
      "basic": int, "total_earnings": int, "total_deductions": int, "net": int,
      "lines": [
        {"line_type": "Earning"|"Deduction", "component_code": str,
         "component_name": str, "amount": int, "basis_amount": int, "rate": float}
      ],
    }

Invariant the reports rely on (and tests assert): total_earnings == basic + Σ
earning-line amounts, and total_deductions == Σ deduction-line amounts.
"""

EARNING = "Earning"
DEDUCTION = "Deduction"
INCOME_TAX = "INCOME_TAX"


def _i(v):
	"""Figures are already integer dinars; coerce None -> 0."""
	return int(v or 0)


def run_summary(rows):
	"""Report 1 — headline totals for a run."""
	return {
		"employees": len(rows),
		"total_basic": sum(_i(r.get("basic")) for r in rows),
		"total_earnings": sum(_i(r.get("total_earnings")) for r in rows),
		"total_deductions": sum(_i(r.get("total_deductions")) for r in rows),
		"total_net": sum(_i(r.get("net")) for r in rows),
	}


def employee_register(rows):
	"""Report 2 — one row per employee (basic / allowances / deductions / net)."""
	out = []
	for r in rows:
		basic = _i(r.get("basic"))
		earnings = _i(r.get("total_earnings"))
		out.append({
			"employee_profile": r.get("employee_profile"),
			"employee_name": r.get("employee_name"),
			"grade_code": r.get("grade_code"),
			"stage": r.get("stage"),
			"basic": basic,
			"allowances": earnings - basic,          # gross = basic + allowances
			"deductions": _i(r.get("total_deductions")),
			"net": _i(r.get("net")),
		})
	totals = {
		"basic": sum(x["basic"] for x in out),
		"allowances": sum(x["allowances"] for x in out),
		"deductions": sum(x["deductions"] for x in out),
		"net": sum(x["net"] for x in out),
	}
	return {"rows": out, "totals": totals}


def _component_register(rows, line_type):
	"""Flat (employee x component) rows for one line_type, plus per-component and
	grand totals. Used by the allowances and deductions registers."""
	out = []
	by_component = {}
	for r in rows:
		for line in r.get("lines") or []:
			if line.get("line_type") != line_type:
				continue
			amount = _i(line.get("amount"))
			code = line.get("component_code")
			out.append({
				"employee_profile": r.get("employee_profile"),
				"employee_name": r.get("employee_name"),
				"component_code": code,
				"component_name": line.get("component_name"),
				"amount": amount,
				"basis_amount": line.get("basis_amount"),
				"rate": line.get("rate"),
			})
			by_component[code] = by_component.get(code, 0) + amount
	return {
		"rows": out,
		"totals_by_component": by_component,
		"grand_total": sum(by_component.values()),
	}


def allowances_register(rows):
	"""Report 3 — earning components per employee (cert / position / risk / ...)."""
	return _component_register(rows, EARNING)


def deductions_register(rows):
	"""Report 4 — deduction components per employee (active pension DED_PENSION,
	income tax, other) — active pension contribution surfaces here."""
	return _component_register(rows, DEDUCTION)


def tax_register(rows):
	"""Report 5 — income tax per employee (amount + taxable basis)."""
	out = []
	total = 0
	for r in rows:
		for line in r.get("lines") or []:
			if line.get("component_code") != INCOME_TAX:
				continue
			amount = _i(line.get("amount"))
			out.append({
				"employee_profile": r.get("employee_profile"),
				"employee_name": r.get("employee_name"),
				"taxable": _i(line.get("basis_amount")),
				"tax": amount,
			})
			total += amount
	return {"rows": out, "total_tax": total}


# Pension register monetary columns (for the totals row).
PENSION_TOTAL_FIELDS = (
	"approved_pension", "certificate_allowance", "cost_of_living", "gross_pension",
	"monthly_tax", "other_deductions", "net_pension", "end_of_service_bonus",
)


def pension_register(rows):
	"""Report 6 — Retirement Pension Register (Phase 4 M11).

	Pass-through of normalized rows (built by the API from stored Pension
	Calculation / Retirement Pension Snapshot values — NO recomputation here) plus
	column totals. Reconciliation the API rows satisfy (asserted in tests):
	gross_pension == approved + certificate + cost_of_living, and
	net_pension == gross_pension - monthly_tax - other_deductions.
	"""
	totals = {f: sum(_i(r.get(f)) for r in rows) for f in PENSION_TOTAL_FIELDS}
	return {"count": len(rows), "rows": rows, "totals": totals}
