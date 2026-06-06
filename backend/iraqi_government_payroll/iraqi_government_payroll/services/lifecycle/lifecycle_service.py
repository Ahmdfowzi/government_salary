# Copyright (c) 2026, Iraqi Government Payroll
"""Employee lifecycle subsystem (Phase 3 M2).

Manages government employee employment status transitions (appointment, transfer,
leave without salary, return, retirement, termination) as permanent auditable
records. The salary/tax/pension/governance engines are untouched — this layer
only manages status and feeds payroll eligibility.

Pure functions (state machine, payroll eligibility, timeline reconstruction) are
unit-testable without a bench. The appoint/transfer/... functions are the
server-side entry points (lazy `import frappe`) that create the audit record and
update the employee profile atomically.
"""

from datetime import date

from ..payroll_engine.types import PayrollError

# Employment statuses
ACTIVE = "Active"
ON_LEAVE = "On Leave Without Salary"
RETIRED = "Retired"
TERMINATED = "Terminated"
EMPLOYMENT_STATUSES = [ACTIVE, ON_LEAVE, RETIRED, TERMINATED]

# event -> (allowed-from statuses, resulting status)  ; "appoint" handled specially
_EVENT_TABLE = {
	"transfer":    ({ACTIVE}, ACTIVE),
	"start_leave": ({ACTIVE}, ON_LEAVE),
	"return":      ({ON_LEAVE}, ACTIVE),
	"retire":      ({ACTIVE, ON_LEAVE}, RETIRED),
	"terminate":   ({ACTIVE, ON_LEAVE}, TERMINATED),
}
EVENT_LABELS = {
	"appoint": "Appointment", "transfer": "Transfer",
	"start_leave": "Leave Without Salary", "return": "Return To Service",
	"retire": "Retirement", "terminate": "Termination",
}


# --------------------------------------------------------------------------- #
# Pure logic                                                                  #
# --------------------------------------------------------------------------- #
def next_status(event, current):
	"""Resulting employment status for `event` from `current`, or raise PayrollError."""
	if event == "appoint":
		return ACTIVE
	if event not in _EVENT_TABLE:
		raise PayrollError(f"Unknown lifecycle event: {event}")
	allowed, target = _EVENT_TABLE[event]
	cur = current or ACTIVE
	if cur not in allowed:
		raise PayrollError(
			f"Cannot apply '{EVENT_LABELS.get(event, event)}' to an employee in status "
			f"'{cur}'. Allowed from: {', '.join(sorted(allowed))}.")
	return target


def is_payroll_eligible(employment_status):
	"""Only Active employees participate in payroll."""
	return (employment_status or ACTIVE) == ACTIVE


def filter_payroll_eligible(profiles):
	"""Drop retired / terminated / on-leave profiles from a payroll candidate list."""
	return [p for p in profiles if is_payroll_eligible(p.get("employment_status"))]


def _to_date(v):
	if isinstance(v, date):
		return v
	return date.fromisoformat(str(v)[:10])


def status_as_of(events, as_of_date):
	"""Reconstruct employment state as of a date from the lifecycle event history.

	events: iterable of dicts {date, event, entity?, position?}. Returns a dict
	with employment_status, current_entity, current_position, last_event,
	last_event_date (None fields if no event applies on/before the date).
	"""
	asof = _to_date(as_of_date)
	state = {"employment_status": None, "current_entity": None, "current_position": None,
			 "last_event": None, "last_event_date": None}
	for e in sorted(events, key=lambda x: _to_date(x["date"])):
		if _to_date(e["date"]) > asof:
			break
		ev = e["event"]
		if ev == "appoint":
			state["employment_status"] = ACTIVE
			state["current_entity"] = e.get("entity")
			state["current_position"] = e.get("position")
		elif ev == "transfer":
			if e.get("entity"):
				state["current_entity"] = e["entity"]
			if e.get("position"):
				state["current_position"] = e["position"]
			state["employment_status"] = ACTIVE
		elif ev == "start_leave":
			state["employment_status"] = ON_LEAVE
		elif ev == "return":
			state["employment_status"] = ACTIVE
		elif ev == "retire":
			state["employment_status"] = RETIRED
		elif ev == "terminate":
			state["employment_status"] = TERMINATED
		state["last_event"] = EVENT_LABELS.get(ev, ev)
		state["last_event_date"] = str(e["date"])
	return state


# --------------------------------------------------------------------------- #
# Server-side entry points (create audit record + update profile)             #
# --------------------------------------------------------------------------- #
def _update_profile(profile, event, *, entity=None, position=None, event_date, extra=None):
	target = next_status(event, profile.get("employment_status"))
	profile.employment_status = target
	if entity is not None:
		profile.current_entity = entity
	if position is not None:
		profile.current_position = position
	for k, v in (extra or {}).items():
		profile.set(k, v)
	profile.last_lifecycle_event = EVENT_LABELS[event]
	profile.last_lifecycle_event_date = event_date
	profile.save()


def appoint_employee(employee, appointment_date, entity=None, position=None,
					 qualification=None, grade_code=None, stage=None, rule_set=None, notes=None):
	import frappe
	if frappe.db.exists("Employee Appointment", {"employee": employee}):
		frappe.throw("This employee already has an appointment record.")
	rec = frappe.get_doc({
		"doctype": "Employee Appointment", "employee": employee,
		"appointment_date": appointment_date, "entity": entity, "position": position,
		"qualification": qualification, "grade_code": grade_code, "stage": stage,
		"rule_set": rule_set, "notes": notes}).insert()
	profile = frappe.get_doc("Government Employee Payroll Profile", employee)
	extra = {}
	if grade_code is not None:
		extra["grade_code"] = grade_code
		if str(grade_code).isdigit():
			extra["current_grade"] = int(grade_code)
	if stage is not None:
		extra["current_stage"] = stage
	if rule_set is not None:
		extra["rule_set"] = rule_set
	_update_profile(profile, "appoint", entity=entity, position=position,
					event_date=appointment_date, extra=extra)
	return rec.name


def transfer_employee(employee, transfer_date, from_entity=None, to_entity=None,
					  from_position=None, to_position=None, reason=None):
	import frappe
	rec = frappe.get_doc({
		"doctype": "Employee Transfer", "employee": employee, "transfer_date": transfer_date,
		"from_entity": from_entity, "to_entity": to_entity, "from_position": from_position,
		"to_position": to_position, "reason": reason}).insert()
	profile = frappe.get_doc("Government Employee Payroll Profile", employee)
	_update_profile(profile, "transfer", entity=to_entity, position=to_position,
					event_date=transfer_date)
	return rec.name


def start_leave_without_salary(employee, start_date, end_date=None, reason=None):
	import frappe
	rec = frappe.get_doc({
		"doctype": "Leave Without Salary", "employee": employee, "start_date": start_date,
		"end_date": end_date, "reason": reason, "status": "Active"}).insert()
	profile = frappe.get_doc("Government Employee Payroll Profile", employee)
	_update_profile(profile, "start_leave", event_date=start_date)
	return rec.name


def return_to_service(employee, return_date, linked_leave=None):
	import frappe
	rec = frappe.get_doc({
		"doctype": "Return To Service", "employee": employee, "return_date": return_date,
		"linked_leave": linked_leave}).insert()
	if linked_leave and frappe.db.exists("Leave Without Salary", linked_leave):
		leave = frappe.get_doc("Leave Without Salary", linked_leave)
		leave.status = "Returned"
		leave.save()
	profile = frappe.get_doc("Government Employee Payroll Profile", employee)
	_update_profile(profile, "return", event_date=return_date)
	return rec.name


def retire_employee(employee, retirement_date, reason=None, pension_calculation=None):
	import frappe
	rec = frappe.get_doc({
		"doctype": "Employee Retirement", "employee": employee,
		"retirement_date": retirement_date, "reason": reason,
		"pension_calculation": pension_calculation}).insert()
	profile = frappe.get_doc("Government Employee Payroll Profile", employee)
	_update_profile(profile, "retire", event_date=retirement_date)
	return rec.name


def terminate_employee(employee, termination_date, reason=None, notes=None):
	import frappe
	rec = frappe.get_doc({
		"doctype": "Employee Termination", "employee": employee,
		"termination_date": termination_date, "reason": reason, "notes": notes}).insert()
	profile = frappe.get_doc("Government Employee Payroll Profile", employee)
	_update_profile(profile, "terminate", event_date=termination_date)
	return rec.name
