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
