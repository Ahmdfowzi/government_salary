# Copyright (c) 2026, Iraqi Government Payroll
"""Promotion service — compute and apply a grade promotion.

Determines target grade/stage so the new salary is not below the old (salary
protection), validates eligibility (years in grade, vacancy, recommendation),
and applies the change to the profile on approval.
Phase 1: signatures only.
"""


def evaluate_promotion(profile_name):
	"""Return proposed target grade/stage/salary for a profile."""
	raise NotImplementedError("Phase 2: implement promotion evaluation.")


def apply_promotion(promotion_request_name):
	"""Apply an approved Promotion Request to the employee profile."""
	raise NotImplementedError("Phase 2: implement promotion application.")
