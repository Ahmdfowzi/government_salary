# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 4 M10 payroll reports (pure + fake-frappe, no bench).

Run:  python3 -m unittest test_reports -v
"""

import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.reports import report_service as rs  # noqa: E402


def _row(emp, name, basic, allowances_lines, deduction_lines):
	"""Build a normalized row; total_earnings = basic + Σ earnings, total_deductions = Σ deductions."""
	earn = sum(a["amount"] for a in allowances_lines)
	ded = sum(d["amount"] for d in deduction_lines)
	lines = (
		[{"line_type": rs.EARNING, **a} for a in allowances_lines]
		+ [{"line_type": rs.DEDUCTION, **d} for d in deduction_lines]
	)
	return {
		"employee_profile": emp, "employee_name": name, "grade_code": "7", "stage": 1,
		"basic": basic, "total_earnings": basic + earn,
		"total_deductions": ded, "net": basic + earn - ded, "lines": lines,
	}


# Two employees with realistic components.
ROWS = [
	_row("E1", "Ali", 296000,
		 [{"component_code": "ALLOW_CERT", "component_name": "Certificate", "amount": 133200,
		   "basis_amount": 296000, "rate": 45}],
		 [{"component_code": "INCOME_TAX", "component_name": "Income Tax", "amount": 57713,
		   "basis_amount": 429200, "rate": None}]),
	_row("E2", "Sara", 200000,
		 [{"component_code": "ALLOW_POSITION", "component_name": "Position", "amount": 40000,
		   "basis_amount": 200000, "rate": 20}],
		 [{"component_code": "DED_PENSION", "component_name": "Pension", "amount": 24000,
		   "basis_amount": 200000, "rate": 12},
		  {"component_code": "INCOME_TAX", "component_name": "Income Tax", "amount": 18000,
		   "basis_amount": 240000, "rate": None}]),
]


class TestRunSummary(unittest.TestCase):
	def test_totals(self):
		s = rs.run_summary(ROWS)
		self.assertEqual(s["employees"], 2)
		self.assertEqual(s["total_basic"], 496000)
		self.assertEqual(s["total_earnings"], 296000 + 133200 + 200000 + 40000)
		self.assertEqual(s["total_deductions"], 57713 + 24000 + 18000)
		self.assertEqual(s["total_net"], (429200 - 57713) + (240000 - 42000))

	def test_empty(self):
		self.assertEqual(rs.run_summary([]),
						 {"employees": 0, "total_basic": 0, "total_earnings": 0,
						  "total_deductions": 0, "total_net": 0})


class TestEmployeeRegister(unittest.TestCase):
	def test_rows_and_totals(self):
		reg = rs.employee_register(ROWS)
		self.assertEqual(len(reg["rows"]), 2)
		ali = reg["rows"][0]
		self.assertEqual(ali["basic"], 296000)
		self.assertEqual(ali["allowances"], 133200)         # earnings - basic
		self.assertEqual(ali["deductions"], 57713)
		self.assertEqual(ali["net"], 371487)
		self.assertEqual(reg["totals"]["net"], 371487 + 198000)


class TestComponentRegisters(unittest.TestCase):
	def test_allowances(self):
		reg = rs.allowances_register(ROWS)
		self.assertEqual(reg["totals_by_component"], {"ALLOW_CERT": 133200, "ALLOW_POSITION": 40000})
		self.assertEqual(reg["grand_total"], 173200)
		# every row is an Earning component
		self.assertTrue(all(r["component_code"].startswith("ALLOW_") for r in reg["rows"]))

	def test_deductions_include_active_pension(self):
		reg = rs.deductions_register(ROWS)
		self.assertEqual(reg["totals_by_component"]["DED_PENSION"], 24000)
		self.assertEqual(reg["totals_by_component"]["INCOME_TAX"], 75713)
		self.assertEqual(reg["grand_total"], 99713)

	def test_tax_register(self):
		reg = rs.tax_register(ROWS)
		self.assertEqual(len(reg["rows"]), 2)
		self.assertEqual(reg["total_tax"], 75713)
		self.assertEqual(reg["rows"][0]["taxable"], 429200)


class TestReconciliation(unittest.TestCase):
	"""The core 'no duplicated calc' guard: every register ties back to the slips."""

	def test_registers_reconcile_to_slip_totals(self):
		summary = rs.run_summary(ROWS)
		emp = rs.employee_register(ROWS)
		allow = rs.allowances_register(ROWS)
		ded = rs.deductions_register(ROWS)
		tax = rs.tax_register(ROWS)
		# allowances grand total == Σ (earnings - basic)
		self.assertEqual(allow["grand_total"], emp["totals"]["allowances"])
		# deductions grand total == Σ deductions == summary deductions
		self.assertEqual(ded["grand_total"], emp["totals"]["deductions"])
		self.assertEqual(ded["grand_total"], summary["total_deductions"])
		# tax is a subset of deductions
		self.assertLessEqual(tax["total_tax"], ded["grand_total"])
		# net == earnings - deductions
		self.assertEqual(summary["total_net"],
						 summary["total_earnings"] - summary["total_deductions"])


# --------------------------- API source selection (fake frappe) --------------------------- #
def _raise(msg):
	raise RuntimeError(msg)


class TestReportSourceSelection(unittest.TestCase):
	"""Locked run -> Snapshot; otherwise -> Salary Slip."""

	def _load_api(self, *, workflow_state):
		queried = []
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.db = types.SimpleNamespace(
			get_value=lambda dt, name, field: workflow_state)

		def get_all(dt, filters=None, fields=None, **k):
			queried.append(dt)
			if dt == "Salary Slip":
				return [{"name": "SLIP-1", "employee_profile": "E1", "employee_name": "Ali",
						 "grade_code": "7", "stage": 1, "basic_salary": 296000,
						 "total_earnings": 429200, "total_deductions": 57713, "net_salary": 371487}]
			if dt == "Salary Slip Line":
				return [{"parent": "SLIP-1", "line_type": "Deduction",
						 "component_code": "INCOME_TAX", "component_name": "Income Tax",
						 "amount": 57713, "basis_amount": 429200, "rate": None}]
			if dt == "Payroll Calculation Snapshot":
				return [{"name": "SNAP-1", "employee_profile": "E1", "employee_name": "Ali",
						 "grade_code": "7", "stage": 1, "gross_amount": 429200,
						 "total_deductions": 57713, "net_amount": 371487}]
			if dt == "Payroll Calculation Snapshot Line":
				return [{"parent": "SNAP-1", "line_type": "Earning",
						 "component_code": "ALLOW_CERT", "component_name": "Cert",
						 "amount": 133200, "basis_amount": 296000, "rate": 45}]
			return []
		frappe.get_all = get_all

		def whitelist(*a, **k):
			def deco(f):
				return f
			return deco if not (a and callable(a[0])) else a[0]
		frappe.whitelist = whitelist
		sys.modules["frappe"] = frappe
		import importlib
		mod = importlib.import_module("iraqi_government_payroll.api.reports_api")
		importlib.reload(mod)
		return mod, queried

	def test_active_run_reads_salary_slip(self):
		api, queried = self._load_api(workflow_state="Calculated")
		res = api.run_summary("RUN-1")
		self.assertIn("Salary Slip", queried)
		self.assertNotIn("Payroll Calculation Snapshot", queried)
		self.assertEqual(res["total_net"], 371487)

	def test_locked_run_reads_snapshot(self):
		api, queried = self._load_api(workflow_state="Locked")
		res = api.run_summary("RUN-1")
		self.assertIn("Payroll Calculation Snapshot", queried)
		self.assertEqual(res["employees"], 1)
		# basic recovered from gross - earnings (429200 - 133200)
		emp = api.employee_register("RUN-1")
		self.assertEqual(emp["rows"][0]["basic"], 296000)
		self.assertEqual(emp["rows"][0]["allowances"], 133200)


if __name__ == "__main__":
	unittest.main()
