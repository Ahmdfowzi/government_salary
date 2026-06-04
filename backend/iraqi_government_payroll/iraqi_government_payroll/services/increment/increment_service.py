# Copyright (c) 2026, Iraqi Government Payroll
"""Increment service — compute and apply the annual increment (one stage up).

Phase 1: signatures only.
"""


def evaluate_increment(profile_name):
	"""Return next stage / new salary / increment amount for a profile."""
	raise NotImplementedError("Phase 2: implement increment evaluation.")


def apply_increment(increment_request_name):
	"""Apply an approved Annual Increment Request to the employee profile."""
	raise NotImplementedError("Phase 2: implement increment application.")
