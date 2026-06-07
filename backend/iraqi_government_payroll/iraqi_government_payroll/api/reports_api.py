# Copyright (c) 2026, Iraqi Government Payroll
"""Read-only payroll report endpoints (Phase 4 M10).

Thin Frappe wiring over services/reports/report_service.py: fetch the per-employee
rows for a run, then delegate aggregation to the pure service. No calculation is
performed here or in the service — reports only sum already-computed figures.

Source selection: a LOCKED run is read from the immutable Payroll Calculation
Snapshot (historical integrity); any other run is read from the live Salary Slip.
"""

import json

import frappe

from iraqi_government_payroll.services.reports import report_service as rs
from iraqi_government_payroll.services.payroll_engine import governance

_LINE_FIELDS = ["line_type", "component_code", "component_name", "amount", "basis_amount", "rate"]


def _line(row):
	return {
		"line_type": row.get("line_type"),
		"component_code": row.get("component_code"),
		"component_name": row.get("component_name"),
		"amount": row.get("amount") or 0,
		"basis_amount": row.get("basis_amount"),
		"rate": row.get("rate"),
	}


def _group_lines(child_doctype, parents):
	"""Return {parent: [normalized line, ...]} for a child table in one query."""
	out = {}
	if not parents:
		return out
	for line in frappe.get_all(child_doctype, filters={"parent": ["in", parents]},
							   fields=["parent"] + _LINE_FIELDS):
		out.setdefault(line["parent"], []).append(_line(line))
	return out


def _slip_rows(run):
	"""Normalized rows from the live Salary Slips of a run."""
	slips = frappe.get_all(
		"Salary Slip", filters={"payroll_run": run},
		fields=["name", "employee_profile", "employee_name", "grade_code", "stage",
				"basic_salary", "total_earnings", "total_deductions", "net_salary"])
	lines = _group_lines("Salary Slip Line", [s["name"] for s in slips])
	rows = []
	for s in slips:
		rows.append({
			"employee_profile": s.get("employee_profile"),
			"employee_name": s.get("employee_name"),
			"grade_code": s.get("grade_code"),
			"stage": s.get("stage"),
			"basic": s.get("basic_salary") or 0,
			"total_earnings": s.get("total_earnings") or 0,
			"total_deductions": s.get("total_deductions") or 0,
			"net": s.get("net_salary") or 0,
			"lines": lines.get(s["name"], []),
		})
	return rows


def _snapshot_rows(run):
	"""Normalized rows from the immutable Salary Slip snapshots of a locked run."""
	slips = frappe.get_all("Salary Slip", filters={"payroll_run": run}, fields=["name"])
	slip_names = [s["name"] for s in slips]
	if not slip_names:
		return []
	snaps = frappe.get_all(
		"Payroll Calculation Snapshot",
		filters={"salary_slip": ["in", slip_names], "calculation_type": "Salary Slip"},
		fields=["name", "employee_profile", "employee_name", "grade_code", "stage",
				"gross_amount", "total_deductions", "net_amount"])
	lines = _group_lines("Payroll Calculation Snapshot Line", [s["name"] for s in snaps])
	rows = []
	for sn in snaps:
		row_lines = lines.get(sn["name"], [])
		gross = sn.get("gross_amount") or 0
		# gross = basic + Σ earnings; recover basic by subtraction (no recompute).
		earnings = sum((ln["amount"] or 0) for ln in row_lines if ln["line_type"] == rs.EARNING)
		rows.append({
			"employee_profile": sn.get("employee_profile"),
			"employee_name": sn.get("employee_name"),
			"grade_code": sn.get("grade_code"),
			"stage": sn.get("stage"),
			"basic": gross - earnings,
			"total_earnings": gross,
			"total_deductions": sn.get("total_deductions") or 0,
			"net": sn.get("net_amount") or 0,
			"lines": row_lines,
		})
	return rows


def _rows_for(run):
	state = frappe.db.get_value("Payroll Run", run, "workflow_state")
	if governance.is_locked(state):
		return _snapshot_rows(run)
	return _slip_rows(run)


@frappe.whitelist()
def run_summary(run):
	return {"run": run, **rs.run_summary(_rows_for(run))}


@frappe.whitelist()
def employee_register(run):
	return {"run": run, **rs.employee_register(_rows_for(run))}


@frappe.whitelist()
def allowances_register(run):
	return {"run": run, **rs.allowances_register(_rows_for(run))}


@frappe.whitelist()
def deductions_register(run):
	return {"run": run, **rs.deductions_register(_rows_for(run))}


@frappe.whitelist()
def tax_register(run):
	return {"run": run, **rs.tax_register(_rows_for(run))}


_BANK_FIELDS = ["name", "iban", "bank_name", "bank_account", "national_id"]


@frappe.whitelist()
def bank_transfer(run):
	"""Bank Transfer Export (M12): net salary per employee (from the live Salary
	Slip for an active run, or the immutable Snapshot for a locked run — via
	_rows_for) joined to the profile's bank details. Net is read, never recomputed;
	rows with no payable account or non-positive net are flagged (see
	report_service.bank_transfer), never skipped."""
	rows = _rows_for(run)
	emps = [r["employee_profile"] for r in rows if r.get("employee_profile")]
	bank = {}
	if emps:
		for b in frappe.get_all("Government Employee Payroll Profile",
								filters={"name": ["in", emps]}, fields=_BANK_FIELDS):
			bank[b["name"]] = b
	enriched = []
	for r in rows:
		b = bank.get(r.get("employee_profile"), {})
		enriched.append({
			"employee_profile": r.get("employee_profile"),
			"employee_name": r.get("employee_name"),
			"net": r.get("net") or 0,
			"iban": b.get("iban"),
			"bank_name": b.get("bank_name"),
			"bank_account": b.get("bank_account"),
			"national_id": b.get("national_id"),
		})
	return {"run": run, **rs.bank_transfer(enriched)}


# --------------------------- Retirement Pension Register (M11) --------------------------- #
# Pension Calculation is per-employee and on-demand (not tied to a Payroll Run), so
# this register is filtered by calculation_date range + status. Source selection
# mirrors M10: a FINALIZED record (status Approved) reads its monetary figures from
# the immutable Retirement Pension snapshot; otherwise from the live record.
# Identity/metadata (employee, name, qualification, status, calculation_date) come
# from the live record + profile — the pension snapshot does not store them.

# Pension Calculation columns (qualification is NOT here — it comes from the profile).
_PENSION_FIELDS = [
	"name", "employee_profile", "employee_name", "calculation_date",
	"status", "period_date", "service_years", "average_36_months", "approved_pension",
	"certificate_allowance", "cost_of_living", "gross_pension", "monthly_tax",
	"other_deductions", "net_pension", "end_of_service_bonus",
]

_FINALIZED = "Approved"


def _qualification(emp, cache):
	if emp not in cache:
		cache[emp] = frappe.db.get_value(
			"Government Employee Payroll Profile", emp, "qualification") or ""
	return cache[emp]


def _pension_row_from_live(rec, qual):
	return {
		"employee_profile": rec.get("employee_profile"),
		"employee_name": rec.get("employee_name"),
		"qualification": qual,
		"service_years": rec.get("service_years") or 0,
		"average_36_months": rec.get("average_36_months") or 0,
		"approved_pension": rec.get("approved_pension") or 0,
		"certificate_allowance": rec.get("certificate_allowance") or 0,
		"cost_of_living": rec.get("cost_of_living") or 0,
		"gross_pension": rec.get("gross_pension") or 0,
		"monthly_tax": rec.get("monthly_tax") or 0,
		"other_deductions": rec.get("other_deductions") or 0,
		"net_pension": rec.get("net_pension") or 0,
		"end_of_service_bonus": rec.get("end_of_service_bonus") or 0,
		"status": rec.get("status"),
		"calculation_date": rec.get("calculation_date"),
	}


def _retirement_snapshot(employee_profile, period_date):
	"""Latest immutable Retirement Pension snapshot for (employee, period), or None."""
	if not period_date:
		return None
	found = frappe.get_all(
		"Payroll Calculation Snapshot",
		filters={"employee_profile": employee_profile, "period_date": period_date,
				 "calculation_type": "Retirement Pension"},
		fields=["name", "employee_name", "gross_amount", "net_amount", "output_snapshot"],
		order_by="creation desc", limit_page_length=1)
	return found[0] if found else None


def _pension_row_from_snapshot(snap, rec, qual):
	"""Monetary fields from the immutable snapshot's output JSON; identity/date from
	the (finalized) live record. service_years recovered from stored service_months."""
	out = json.loads(snap.get("output_snapshot") or "{}")
	return {
		"employee_profile": rec.get("employee_profile"),
		"employee_name": rec.get("employee_name") or snap.get("employee_name"),
		"qualification": qual,
		"service_years": int(out.get("service_months") or 0) // 12,
		"average_36_months": out.get("avg36") or 0,
		"approved_pension": out.get("approved_pension") or 0,
		"certificate_allowance": out.get("certificate_allowance") or 0,
		"cost_of_living": out.get("cost_of_living") or 0,
		"gross_pension": out.get("gross_pension") or snap.get("gross_amount") or 0,
		"monthly_tax": out.get("monthly_tax") or 0,
		"other_deductions": out.get("other_deductions") or 0,
		"net_pension": out.get("net_pension") or snap.get("net_amount") or 0,
		"end_of_service_bonus": out.get("end_of_service_bonus") or 0,
		"status": _FINALIZED,                         # a snapshot exists -> finalized
		"calculation_date": rec.get("calculation_date"),
	}


@frappe.whitelist()
def pension_register(from_date=None, to_date=None, status=None):
	"""Retirement Pension Register filtered by calculation_date range + status."""
	filters = {}
	if from_date and to_date:
		filters["calculation_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["calculation_date"] = [">=", from_date]
	elif to_date:
		filters["calculation_date"] = ["<=", to_date]
	if status:
		filters["status"] = status

	records = frappe.get_all("Pension Calculation", filters=filters, fields=_PENSION_FIELDS)
	qual_cache = {}
	rows = []
	for rec in records:
		qual = _qualification(rec.get("employee_profile"), qual_cache)
		snap = (_retirement_snapshot(rec.get("employee_profile"), rec.get("period_date"))
				if rec.get("status") == _FINALIZED else None)
		rows.append(_pension_row_from_snapshot(snap, rec, qual) if snap
					else _pension_row_from_live(rec, qual))

	return {"from_date": from_date, "to_date": to_date, "status": status,
			**rs.pension_register(rows)}
