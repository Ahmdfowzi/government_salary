# Copyright (c) 2026, Iraqi Government Payroll
"""Allowance service — resolve components and apply the 200% cap.

Reads active Allowance Rule rows for the relevant context (Active vs Pension)
and effective date, computes percentage components on BASIC only, then applies
the 200% cap to the capped subset.
Phase 1: signatures only.
"""


def resolve_allowances(profile, basic_salary, context, period_date):
	"""Return capped + non-capped allowance lines for a profile."""
	raise NotImplementedError("Phase 2: implement allowance resolution.")


def apply_200_percent_cap(basic_salary, capped_components):
	"""Cap the sum of capped allowances at 200% of basic; flag violations."""
	raise NotImplementedError("Phase 2: implement 200% cap.")
