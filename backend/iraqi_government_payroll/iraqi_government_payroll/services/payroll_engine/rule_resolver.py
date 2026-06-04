# Copyright (c) 2026, Iraqi Government Payroll
"""Rule Set Resolver — pick exactly one Active Government Rule Set by period date."""

from datetime import date
from .types import PayrollError


def _to_date(value):
	if value is None or value == "":
		return None
	if isinstance(value, date):
		return value
	return date.fromisoformat(str(value)[:10])


def resolve_rule_set(rule_sets, period_date):
	"""Return the single Active rule set whose effective window contains period_date.

	Rule: ``effective_from <= period_date < effective_to`` (empty effective_to = open).
	Raises PayrollError if zero or more than one Active rule set matches.
	"""
	pd = _to_date(period_date)
	if pd is None:
		raise PayrollError("period_date is required to resolve a rule set")

	matches = []
	for rs in rule_sets:
		if str(rs.get("status") or "").lower() != "active":
			continue
		ef = _to_date(rs.get("effective_from"))
		et = _to_date(rs.get("effective_to"))
		if ef and pd < ef:
			continue
		if et and pd >= et:
			continue
		matches.append(rs)

	if not matches:
		raise PayrollError(f"No Active Government Rule Set is effective on {pd.isoformat()}")
	if len(matches) > 1:
		codes = [m.get("name") or m.get("rule_set_code") for m in matches]
		raise PayrollError(
			f"Multiple Active Government Rule Sets effective on {pd.isoformat()}: {codes}"
		)
	return matches[0]
