# Copyright (c) 2026, Iraqi Government Payroll
"""Payroll Period validation helpers (pure, no Frappe)."""

from datetime import date
from .types import PayrollError

ALLOWED_TRANSITIONS = {
	"Draft": {"Draft", "Open"},
	"Open": {"Open", "Closed"},
	"Closed": {"Closed"},
}


def _d(v):
	if isinstance(v, date):
		return v
	return date.fromisoformat(str(v)[:10])


def validate_period_dates(year, month, start_date, end_date):
	"""start_date <= end_date and both fall within the period's year/month."""
	if not (1 <= int(month) <= 12):
		raise PayrollError("month must be between 1 and 12")
	s, e = _d(start_date), _d(end_date)
	if s > e:
		raise PayrollError("start_date must be on or before end_date")
	if s.year != int(year) or s.month != int(month):
		raise PayrollError("start_date must fall within the period year/month")
	if e.year != int(year) or e.month != int(month):
		raise PayrollError("end_date must fall within the period year/month")
	return True


def validate_status_transition(old_status, new_status):
	"""Allowed flow: Draft -> Open -> Closed (and no-op same-state)."""
	old = old_status or "Draft"
	if new_status not in ALLOWED_TRANSITIONS.get(old, set()):
		raise PayrollError(f"Invalid payroll period status transition: {old} -> {new_status}")
	return True


def check_duplicate(year, month, existing_keys):
	"""Raise if a period for (year, month) already exists. existing_keys: iterable of (year, month)."""
	target = (int(year), int(month))
	for (y, m) in existing_keys:
		if (int(y), int(m)) == target:
			raise PayrollError(f"A payroll period for {year}-{month:0>2} already exists")
	return True
