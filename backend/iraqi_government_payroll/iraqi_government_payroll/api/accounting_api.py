# Copyright (c) 2026, Iraqi Government Payroll
"""Accounting journal export endpoints (Phase 4 M15) — PROPOSAL ONLY.

Builds balanced double-entry journal rows from a payroll run's already-computed
figures + the Payroll Account Mapping. This is an EXPORT only: it never creates a
GL Entry or Journal Entry, never submits anything, and never changes payroll
amounts. Read-only.

Source selection is inherited from the reports layer: a Locked run is read from
the immutable Snapshot; any other run from the live Salary Slip.
"""

import frappe

from iraqi_government_payroll.api.reports_api import _rows_for
from iraqi_government_payroll.services.accounting import journal_service as js
from iraqi_government_payroll.services.reports import xlsx_export

_MAPPING_FIELDS = [
	"salary_expense_account", "allowance_expense_account", "employee_payable_account",
	"pension_payable_account", "tax_payable_account", "other_deductions_payable_account",
]

_JOURNAL_COLUMNS = [
	("account", "الحساب"),
	("description", "البيان"),
	("debit", "مدين"),
	("credit", "دائن"),
]


def _mapping():
	doc = frappe.get_single("Payroll Account Mapping")
	return {f: (doc.get(f) or "").strip() for f in _MAPPING_FIELDS}


def _build(run):
	"""Balanced journal for a run; fails safely on an incomplete mapping."""
	rows = _rows_for(run)
	try:
		return js.build_journal(rows, _mapping())
	except js.JournalMappingError as exc:
		frappe.throw(
			"Accounting journal export needs an account mapping for: "
			+ ", ".join(exc.missing)
			+ ". Configure it in Payroll Account Mapping (no ledger posting happens).")
	except js.JournalImbalanceError as exc:
		frappe.throw(f"Accounting journal is not balanced: {exc}")


@frappe.whitelist()
def journal_export(run):
	"""Read-only balanced journal proposal for a payroll run. No GL posting."""
	return {"run": run, **_build(run)}


@frappe.whitelist()
def export_journal(run, fmt="xlsx"):
	"""Download the journal proposal as a file (xlsx). No GL posting."""
	if fmt != "xlsx":
		frappe.throw(f"Unsupported export format: {fmt}")
	data = _build(run)
	content = xlsx_export.build_workbook(
		"قيد الرواتب المحاسبي", _JOURNAL_COLUMNS, data["rows"],
		totals={"debit": data["total_debit"], "credit": data["total_credit"]})
	frappe.response["filename"] = f"journal-{run}.xlsx"
	frappe.response["filecontent"] = content
	frappe.response["type"] = "binary"
