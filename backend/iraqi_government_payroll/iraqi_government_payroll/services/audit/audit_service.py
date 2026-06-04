# Copyright (c) 2026, Iraqi Government Payroll
"""Audit service — write immutable Salary Calculation Log entries.

Every calculation (active salary, increment, promotion, pension, tax) produces
one write-once log with totals, an explained line breakdown and full
input/output JSON snapshots.
Phase 1: signatures only.
"""


def write_calculation_log(calculation_type, profile, context, lines, totals, snapshots):
	"""Create one immutable Salary Calculation Log + its lines."""
	raise NotImplementedError("Phase 2: implement audit log writing.")
