# Copyright (c) 2026, Iraqi Government Payroll
"""Read-only payroll report endpoints (Phase 4 M10).

Thin Frappe wiring over services/reports/report_service.py: fetch the per-employee
rows for a run, then delegate aggregation to the pure service. No calculation is
performed here or in the service — reports only sum already-computed figures.

Source selection: a LOCKED run is read from the immutable Payroll Calculation
Snapshot (historical integrity); any other run is read from the live Salary Slip.
"""

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
