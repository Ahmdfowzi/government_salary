# Copyright (c) 2026, Iraqi Government Payroll
"""Historical integrity & payroll history queries (Phase 3 M3).

Past payroll is reconstructed from IMMUTABLE Payroll Calculation Snapshots
(salary figures) combined with the IMMUTABLE employee lifecycle timeline
(status/entity/position). Because both sources are write-once, changing an
employee's current profile can never alter historical payroll.

This module also provides the retroactive-change guard: a lifecycle/transaction
event dated on or before the end of any LOCKED payroll period for that employee
is rejected, so locked history is never invalidated.
"""

from datetime import date

from ..payroll_engine.types import PayrollError
from ..lifecycle import lifecycle_service as lifecycle


# --------------------------------------------------------------------------- #
# Pure helpers                                                                #
# --------------------------------------------------------------------------- #
def _to_date(v):
	if isinstance(v, date):
		return v
	return date.fromisoformat(str(v)[:10])


def is_retroactive_to_locked(effective_date, locked_period_ends):
	"""True if effective_date falls on/before the end of any locked payroll period."""
	if not locked_period_ends:
		return False
	eff = _to_date(effective_date)
	return any(eff <= _to_date(end) for end in locked_period_ends)


def latest_snapshot_on_or_before(snapshots, as_of_date):
	"""Return the snapshot with the greatest period_date <= as_of_date (or None)."""
	asof = _to_date(as_of_date)
	eligible = [s for s in snapshots if s.get("period_date") and _to_date(s["period_date"]) <= asof]
	if not eligible:
		return None
	return max(eligible, key=lambda s: _to_date(s["period_date"]))


def reconstruct_state(snapshots, lifecycle_events, as_of_date):
	"""Reconstruct an employee's historical state at a date.

	Salary figures come from the latest payroll snapshot on/before the date;
	status/entity/position from the lifecycle timeline. Pure — never reads the
	live profile, so current changes cannot alter the result.
	"""
	snap = latest_snapshot_on_or_before(snapshots, as_of_date)
	timeline = lifecycle.status_as_of(lifecycle_events, as_of_date)
	return {
		"as_of": str(as_of_date),
		"employment_status": timeline["employment_status"],
		"entity": timeline["current_entity"],
		"position": timeline["current_position"],
		"payroll": {
			"period_date": snap.get("period_date") if snap else None,
			"grade_code": snap.get("grade_code") if snap else None,
			"stage": snap.get("stage") if snap else None,
			"rule_set": snap.get("rule_set") if snap else None,
			"gross_amount": snap.get("gross_amount") if snap else None,
			"total_deductions": snap.get("total_deductions") if snap else None,
			"net_amount": snap.get("net_amount") if snap else None,
		} if snap else None,
	}


# --------------------------------------------------------------------------- #
# Frappe-backed queries                                                       #
# --------------------------------------------------------------------------- #
def get_employee_payroll_history(employee):
	"""All Salary Slip snapshots for an employee, oldest first (immutable history)."""
	import frappe
	return frappe.get_all(
		"Payroll Calculation Snapshot",
		filters={"employee_profile": employee, "calculation_type": "Salary Slip"},
		fields=["name", "salary_slip", "payroll_period", "period_date", "rule_set",
				"grade_code", "stage", "gross_amount", "total_deductions", "net_amount"],
		order_by="period_date asc")


def get_payroll_snapshot(run, employee):
	"""The immutable snapshot for one (payroll run, employee)."""
	import frappe
	slip = frappe.db.get_value(
		"Salary Slip", {"payroll_run": run, "employee_profile": employee}, "name")
	if not slip:
		return None
	name = frappe.db.get_value(
		"Payroll Calculation Snapshot", {"salary_slip": slip, "calculation_type": "Salary Slip"}, "name")
	return frappe.get_doc("Payroll Calculation Snapshot", name).as_dict() if name else None


def _lifecycle_events(employee):
	"""Collect the immutable lifecycle event timeline for an employee."""
	import frappe
	events = []
	for r in frappe.get_all("Employee Appointment", filters={"employee": employee},
							fields=["appointment_date", "entity", "position"]):
		events.append({"date": r["appointment_date"], "event": "appoint",
					   "entity": r["entity"], "position": r["position"]})
	for r in frappe.get_all("Employee Transfer", filters={"employee": employee},
							fields=["transfer_date", "to_entity", "to_position"]):
		events.append({"date": r["transfer_date"], "event": "transfer",
					   "entity": r["to_entity"], "position": r["to_position"]})
	for r in frappe.get_all("Leave Without Salary", filters={"employee": employee},
							fields=["start_date"]):
		events.append({"date": r["start_date"], "event": "start_leave"})
	for r in frappe.get_all("Return To Service", filters={"employee": employee},
							fields=["return_date"]):
		events.append({"date": r["return_date"], "event": "return"})
	for r in frappe.get_all("Employee Retirement", filters={"employee": employee},
							fields=["retirement_date"]):
		events.append({"date": r["retirement_date"], "event": "retire"})
	for r in frappe.get_all("Employee Termination", filters={"employee": employee},
							fields=["termination_date"]):
		events.append({"date": r["termination_date"], "event": "terminate"})
	return [e for e in events if e.get("date")]


def get_employee_state_at_date(employee, as_of_date):
	"""Reconstruct historical state from immutable snapshots + lifecycle timeline."""
	snapshots = get_employee_payroll_history(employee)
	events = _lifecycle_events(employee)
	return reconstruct_state(snapshots, events, as_of_date)


def locked_period_ends_for_employee(employee):
	"""End dates of every LOCKED payroll period the employee participated in."""
	import frappe
	locked_runs = [r["name"] for r in frappe.get_all(
		"Payroll Run", filters={"workflow_state": "Locked"}, fields=["name"])]
	if not locked_runs:
		return []
	periods = [s["payroll_period"] for s in frappe.get_all(
		"Salary Slip",
		filters={"payroll_run": ["in", locked_runs], "employee_profile": employee},
		fields=["payroll_period"]) if s.get("payroll_period")]
	ends = []
	for p in set(periods):
		end = frappe.db.get_value("Payroll Period", p, "end_date")
		if end:
			ends.append(end)
	return ends


# Per-doctype extraction of (employee, effective_date) for the retroactive guard.
_GUARD_MAP = {
	"Promotion Request": ("employee_profile", "due_date"),
	"Employee Transfer": ("employee", "transfer_date"),
	"Employee Retirement": ("employee", "retirement_date"),
}


def guard_retroactive_change(doc, method=None):
	"""doc_events validate hook: block changes dated into a locked payroll period."""
	mapping = _GUARD_MAP.get(doc.doctype)
	if not mapping:
		return
	emp_field, date_field = mapping
	employee = doc.get(emp_field)
	effective_date = doc.get(date_field)
	if not (employee and effective_date):
		return
	ends = locked_period_ends_for_employee(employee)
	if is_retroactive_to_locked(effective_date, ends):
		import frappe
		frappe.throw(
			f"Cannot record a {doc.doctype} dated {effective_date}: it falls within a "
			f"locked payroll period for this employee. Locked history is immutable.")
