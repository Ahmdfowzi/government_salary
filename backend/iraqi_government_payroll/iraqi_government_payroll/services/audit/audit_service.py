# Copyright (c) 2026, Iraqi Government Payroll
"""Audit service — build & write immutable Payroll Calculation Snapshot entries.

``build_snapshot_payload`` is pure (no Frappe) and unit-testable. ``write_snapshot``
inserts the immutable record via Frappe (only when explicitly requested). M3 does
NOT create a Salary Slip and records no deductions (net == gross).
"""

import json
from dataclasses import asdict


def build_snapshot_payload(result, employee_input=None, employee_profile=None,
						   calculation_type="Active Salary"):
	"""Return the dict payload for a Payroll Calculation Snapshot from a result."""
	input_snapshot = asdict(employee_input) if employee_input is not None else {}
	output_snapshot = result.to_dict()

	lines = [{
		"doctype": "Payroll Calculation Snapshot Line",
		"component_code": l.component_code,
		"component_name": l.component_name,
		"line_type": l.line_type,
		"amount": l.amount,
		"basis_amount": l.basis_amount,
		"rate": l.rate,
		"cap_applied": 1 if l.cap_applied else 0,
		"source_rule": l.source_rule,
		"reason_text": l.reason_text,
	} for l in result.allowance_lines]

	return {
		"doctype": "Payroll Calculation Snapshot",
		"calculation_type": calculation_type,
		"employee_profile": employee_profile,
		"rule_set": result.rule_set,
		"rule_set_version": result.rule_set,
		"engine_version": result.engine_version,
		"period_date": result.period_date,
		"grade_code": result.grade_code,
		"stage": result.stage,
		"gross_amount": result.gross_salary,
		"total_deductions": 0,            # M3: no deductions
		"net_amount": result.gross_salary,
		"input_snapshot": json.dumps(input_snapshot, ensure_ascii=False, default=str),
		"output_snapshot": json.dumps(output_snapshot, ensure_ascii=False, default=str),
		"lines": lines,
	}


def build_generic_snapshot_payload(calculation_type, *, rule_set, engine_version,
								   period_date=None, gross_amount=0, total_deductions=0,
								   net_amount=0, lines=None, input_obj=None, output_obj=None,
								   employee_profile=None, grade_code="", stage=0):
	"""Build a snapshot payload for non-active-salary calculations.

	Supports calculation_type "Tax", "Pension Deduction" and "Retirement Pension".
	``lines`` is a list of dicts (component_code, component_name, line_type, amount,
	basis_amount, rate, cap_applied, source_rule, reason_text).
	"""
	snapshot_lines = []
	for l in (lines or []):
		snapshot_lines.append({
			"doctype": "Payroll Calculation Snapshot Line",
			"component_code": l.get("component_code", ""),
			"component_name": l.get("component_name", ""),
			"line_type": l.get("line_type", ""),
			"amount": l.get("amount", 0),
			"basis_amount": l.get("basis_amount", 0),
			"rate": l.get("rate"),
			"cap_applied": 1 if l.get("cap_applied") else 0,
			"source_rule": l.get("source_rule", ""),
			"reason_text": l.get("reason_text", ""),
		})
	return {
		"doctype": "Payroll Calculation Snapshot",
		"calculation_type": calculation_type,
		"employee_profile": employee_profile,
		"rule_set": rule_set,
		"rule_set_version": rule_set,
		"engine_version": engine_version,
		"period_date": period_date,
		"grade_code": grade_code,
		"stage": stage,
		"gross_amount": gross_amount,
		"total_deductions": total_deductions,
		"net_amount": net_amount,
		"input_snapshot": json.dumps(input_obj or {}, ensure_ascii=False, default=str),
		"output_snapshot": json.dumps(output_obj or {}, ensure_ascii=False, default=str),
		"lines": snapshot_lines,
	}


def build_retirement_pension_snapshot_payload(result, pension_input=None, employee_profile=None):
	"""Build a 'Retirement Pension' snapshot payload from a RetirementPensionResult."""
	lines = [
		{"component_code": "PENSION_APPROVED", "component_name": "Approved Pension",
		 "line_type": "Earning", "amount": result.approved_pension},
		{"component_code": "PENSION_CERTIFICATE", "component_name": "Certificate Allowance",
		 "line_type": "Earning", "amount": result.certificate_allowance},
		{"component_code": "PENSION_COL", "component_name": "Cost of Living",
		 "line_type": "Earning", "amount": result.cost_of_living},
		{"component_code": "PENSION_TAX", "component_name": "Monthly Tax",
		 "line_type": "Deduction", "amount": result.monthly_tax},
	]
	return build_generic_snapshot_payload(
		"Retirement Pension",
		rule_set=result.rule_set,
		engine_version=result.engine_version,
		period_date=result.period_date,
		gross_amount=result.gross_pension,
		total_deductions=result.monthly_tax + result.other_deductions,
		net_amount=result.net_pension,
		lines=lines,
		input_obj=(pension_input.__dict__ if pension_input is not None else {}),
		output_obj=result.to_dict(),
		employee_profile=employee_profile,
	)


def write_snapshot(result, employee_input=None, employee_profile=None,
				   calculation_type="Active Salary"):
	"""Insert an immutable Payroll Calculation Snapshot. Returns its name."""
	import frappe

	payload = build_snapshot_payload(result, employee_input, employee_profile, calculation_type)
	if not payload.get("calc_timestamp"):
		payload["calc_timestamp"] = frappe.utils.now()
	doc = frappe.get_doc(payload)
	doc.insert()
	return doc.name
