# Copyright (c) 2026, Iraqi Government Payroll
"""Frappe-backed data loader for the active-salary engine.

This is the production wiring: it reads the rule set / scale / allowance data
from the Frappe DB and builds a DataContext, then delegates to the pure engine.
``frappe`` is imported lazily so the pure engine modules stay testable without a
bench.
"""

from .engine import DataContext, EmployeeInput, calculate_active_salary
from .scale_resolver import resolve_grade_code


def load_context() -> "DataContext":
	import frappe

	rule_sets = frappe.get_all(
		"Government Rule Set",
		fields=["name", "rule_set_code", "status", "effective_from", "effective_to"],
	)

	scales = []
	for s in frappe.get_all("Government Salary Scale", fields=["name", "rule_set", "is_active"]):
		doc = frappe.get_doc("Government Salary Scale", s["name"])
		s["details"] = [
			{"grade_code": d.grade_code, "grade": d.grade, "stage": d.stage,
			 "basic_salary": d.basic_salary}
			for d in doc.details
		]
		scales.append(s)

	allowance_rules = frappe.get_all(
		"Allowance Rule",
		fields=["name", "component_code", "component_name", "rule_set", "allowance_type",
				"context", "match_key", "match_value", "calculation_type", "basis",
				"percentage", "fixed_amount", "capped_under_200", "confirmed", "is_active"],
	)
	return DataContext(rule_sets=rule_sets, scales=scales, allowance_rules=allowance_rules)


def calculate_for_profile(profile_name, period_date):
	"""Convenience entry point: compute active salary for an employee profile.

	Uses profile.grade_code as the canonical key (supports senior grades), and
	falls back to str(current_grade) only when grade_code is empty.
	"""
	import frappe

	p = frappe.get_doc("Government Employee Payroll Profile", profile_name)
	emp = EmployeeInput(
		grade_code=resolve_grade_code(p.get("grade_code"), p.get("current_grade")),
		stage=p.current_stage,
		period_date=period_date,
		qualification=p.qualification,
		position_allowance_category=None,
		risk_applicable=bool(p.risk_allowance_applicable),
		risk_category=p.risk_category,
		spouse_eligible=(p.marital_status == "Married"),
		children_count=p.eligible_children_count or 0,
	)
	return calculate_active_salary(load_context(), emp)
