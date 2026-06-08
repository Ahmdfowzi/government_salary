# Copyright (c) 2026, Iraqi Government Payroll
"""Tests for Phase 4 M15 accounting journal export (pure + fake-frappe, no bench).

Run:  python3 -m unittest test_accounting -v
"""

import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.accounting import journal_service as js  # noqa: E402

FULL_MAP = {
	"salary_expense_account": "5100",
	"allowance_expense_account": "5200",
	"employee_payable_account": "2100",
	"pension_payable_account": "2200",
	"tax_payable_account": "2300",
	"other_deductions_payable_account": "2400",
}


def _row(emp, basic, allowances, ded_lines):
	"""Normalized payroll row; total_earnings = basic + allowances,
	total_deductions = Σ deduction lines, net = earnings - deductions."""
	ded = sum(d["amount"] for d in ded_lines)
	return {
		"employee_profile": emp, "employee_name": emp,
		"basic": basic, "total_earnings": basic + allowances,
		"total_deductions": ded, "net": basic + allowances - ded,
		"lines": [{"line_type": "Deduction", **d} for d in ded_lines]
		+ [{"line_type": "Earning", "component_code": "ALLOW", "amount": allowances}],
	}


ROWS = [
	_row("E1", 296000, 133200, [{"component_code": "INCOME_TAX", "amount": 57713}]),
	_row("E2", 200000, 40000, [{"component_code": "DED_PENSION", "amount": 24000},
							   {"component_code": "INCOME_TAX", "amount": 18000}]),
]


# --------------------------- Pure journal builder --------------------------- #
class TestBalancedJournal(unittest.TestCase):
	def test_balanced_and_totals(self):
		j = js.build_journal(ROWS, FULL_MAP)
		self.assertTrue(j["balanced"])
		self.assertEqual(j["total_debit"], j["total_credit"])
		self.assertEqual(j["total_debit"], 296000 + 200000 + 133200 + 40000)  # Σ earnings
		# other = 0 here, so its credit row is omitted -> 5 rows
		self.assertEqual(len(j["rows"]), 5)

	def test_debit_credit_equal_invariant(self):
		j = js.build_journal(ROWS, FULL_MAP)
		debit = sum(r["debit"] for r in j["rows"])
		credit = sum(r["credit"] for r in j["rows"])
		self.assertEqual(debit, credit)


class TestSeparation(unittest.TestCase):
	def test_allowances_and_deductions_separated(self):
		j = js.build_journal(ROWS, FULL_MAP)
		by_desc = {r["description"]: r for r in j["rows"]}
		# salary vs allowance are distinct DEBIT lines on distinct accounts
		self.assertEqual(by_desc["Salary Expense"]["debit"], 496000)
		self.assertEqual(by_desc["Allowance Expense"]["debit"], 173200)
		self.assertNotEqual(by_desc["Salary Expense"]["account"],
							 by_desc["Allowance Expense"]["account"])
		# deductions split into distinct CREDIT lines
		self.assertEqual(by_desc["Pension Payable"]["credit"], 24000)
		self.assertEqual(by_desc["Tax Payable"]["credit"], 75713)
		self.assertEqual(by_desc["Employee Payable"]["credit"], 569487)
		# every line is purely a debit or a credit, never both
		for r in j["rows"]:
			self.assertTrue((r["debit"] == 0) != (r["credit"] == 0))


class TestMissingMapping(unittest.TestCase):
	def test_missing_required_account_raises(self):
		bad = dict(FULL_MAP); bad["tax_payable_account"] = ""   # tax > 0 -> required
		with self.assertRaises(js.JournalMappingError) as ctx:
			js.build_journal(ROWS, bad)
		self.assertIn("tax_payable_account", ctx.exception.missing)

	def test_account_not_required_when_amount_zero(self):
		# no pension lines anywhere -> pension_payable_account not required
		rows = [_row("E1", 296000, 133200, [{"component_code": "INCOME_TAX", "amount": 57713}])]
		m = dict(FULL_MAP); m["pension_payable_account"] = ""    # missing but unused
		j = js.build_journal(rows, m)
		self.assertTrue(j["balanced"])
		self.assertNotIn("Pension Payable", [r["description"] for r in j["rows"]])


class TestEmptyRun(unittest.TestCase):
	def test_empty_rows_safe_balanced_empty(self):
		j = js.build_journal([], {})                # no rows, no mapping at all
		self.assertEqual(j["rows"], [])
		self.assertEqual(j["total_debit"], 0)
		self.assertEqual(j["total_credit"], 0)
		self.assertTrue(j["balanced"])


# --------------------------- API: source selection + no posting --------------------------- #
def _raise(msg):
	raise RuntimeError(msg)


class TestAccountingApi(unittest.TestCase):
	def _load(self, *, workflow_state, mapping, post_guard=False):
		queried = []
		frappe = types.ModuleType("frappe")
		frappe.throw = lambda msg, *a, **k: _raise(msg)
		frappe._ = lambda s, *a, **k: s
		frappe.response = {}
		frappe.session = types.SimpleNamespace(user="Administrator")
		frappe.get_roles = lambda *a, **k: ["System Manager"]   # superuser -> export allowed
		frappe.db = types.SimpleNamespace(get_value=lambda dt, name, field: workflow_state)
		frappe.get_single = lambda dt: types.SimpleNamespace(get=lambda f: mapping.get(f))

		def get_all(dt, filters=None, fields=None, **k):
			queried.append(dt)
			if dt == "Salary Slip" and fields and "basic_salary" in fields:
				return [{"name": "S1", "employee_profile": "E1", "employee_name": "Ali",
						 "grade_code": "7", "stage": 1, "basic_salary": 296000,
						 "total_earnings": 429200, "total_deductions": 57713, "net_salary": 371487}]
			if dt == "Salary Slip":                          # name-only (snapshot path)
				return [{"name": "S1"}]
			if dt == "Salary Slip Line":
				return [{"parent": "S1", "line_type": "Deduction", "component_code": "INCOME_TAX",
						 "component_name": "Tax", "amount": 57713, "basis_amount": 429200, "rate": None},
						{"parent": "S1", "line_type": "Earning", "component_code": "ALLOW_CERT",
						 "component_name": "Cert", "amount": 133200, "basis_amount": 296000, "rate": 45}]
			if dt == "Payroll Calculation Snapshot":
				return [{"name": "SN1", "employee_profile": "E1", "employee_name": "Ali",
						 "grade_code": "7", "stage": 1, "gross_amount": 429200,
						 "total_deductions": 57713, "net_amount": 371487}]
			if dt == "Payroll Calculation Snapshot Line":
				return [{"parent": "SN1", "line_type": "Deduction", "component_code": "INCOME_TAX",
						 "component_name": "Tax", "amount": 57713, "basis_amount": 429200, "rate": None},
						{"parent": "SN1", "line_type": "Earning", "component_code": "ALLOW_CERT",
						 "component_name": "Cert", "amount": 133200, "basis_amount": 296000, "rate": 45}]
			return []
		frappe.get_all = get_all

		if post_guard:
			def _no_post(*a, **k):
				raise AssertionError("ledger posting attempted: frappe.get_doc called")
			frappe.get_doc = _no_post

		def whitelist(*a, **k):
			def deco(f):
				return f
			return deco if not (a and callable(a[0])) else a[0]
		frappe.whitelist = whitelist
		sys.modules["frappe"] = frappe
		import importlib
		from iraqi_government_payroll.api import reports_api
		importlib.reload(reports_api)                # rebind its `frappe` global
		from iraqi_government_payroll.api import accounting_api
		importlib.reload(accounting_api)             # picks up reloaded _rows_for
		return accounting_api, queried

	def test_active_run_uses_salary_slip(self):
		api, queried = self._load(workflow_state="Calculated", mapping=FULL_MAP)
		res = api.journal_export("RUN-1")
		self.assertIn("Salary Slip", queried)
		self.assertNotIn("Payroll Calculation Snapshot", queried)
		self.assertTrue(res["balanced"])
		self.assertEqual(res["total_debit"], res["total_credit"])

	def test_locked_run_uses_snapshot(self):
		api, queried = self._load(workflow_state="Locked", mapping=FULL_MAP)
		res = api.journal_export("RUN-1")
		self.assertIn("Payroll Calculation Snapshot", queried)   # snapshot source
		self.assertTrue(res["balanced"])
		self.assertEqual(res["total_debit"], 429200)             # Σ earnings from snapshot

	def test_no_ledger_posting_occurs(self):
		# get_doc raises if called; a successful export proves nothing was posted.
		api, _ = self._load(workflow_state="Calculated", mapping=FULL_MAP, post_guard=True)
		res = api.journal_export("RUN-1")          # must not call get_doc / insert / submit
		self.assertTrue(res["balanced"])

	def test_incomplete_mapping_fails_safely(self):
		partial = dict(FULL_MAP); partial["employee_payable_account"] = ""
		api, _ = self._load(workflow_state="Calculated", mapping=partial)
		with self.assertRaises(Exception):
			api.journal_export("RUN-1")


if __name__ == "__main__":
	unittest.main()
