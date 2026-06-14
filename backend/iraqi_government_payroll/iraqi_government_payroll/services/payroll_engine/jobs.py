# Copyright (c) 2026, Iraqi Government Payroll
"""Background jobs for the payroll engine (run via `frappe.enqueue`).

These are Frappe-wiring entry points only: they load the document, run the SAME
calculation path the synchronous controller method uses, and own commit/rollback
so a long run cannot exceed the HTTP timeout. No calculation logic lives here.
"""

import frappe


def run_calculation_job(run_name, user):
	"""Worker entry point for an asynchronous payroll calculation.

	Runs as the requesting `user` so role checks and audit stamps
	(`calculated_by`, governance event actor) match the operator who queued it.
	On a hard failure (e.g. an unconfigured rule set) the run is marked `Failed`
	in its own committed transaction so the UI poll can surface it, then the error
	re-raises so it is recorded in the RQ failed-job registry / error log.

	The calculation itself is `PayrollRun._perform_calculation` →
	`repository.run_payroll`, identical to the synchronous `calculate_run`, so the
	immutable Payroll Calculation Snapshot behaviour is unchanged.
	"""
	frappe.set_user(user)
	doc = frappe.get_doc("Payroll Run", run_name)
	try:
		result = doc._perform_calculation()
		frappe.db.commit()
		return result
	except Exception:
		frappe.db.rollback()
		try:
			frappe.db.set_value("Payroll Run", run_name, "run_status", "Failed",
								update_modified=False)
			frappe.db.commit()
		except Exception:
			frappe.log_error(title="Payroll async run: could not mark Failed")
		frappe.log_error(title=f"Payroll async run failed: {run_name}")
		raise
