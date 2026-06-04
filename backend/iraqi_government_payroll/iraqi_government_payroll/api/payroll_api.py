# Copyright (c) 2026, Iraqi Government Payroll
"""Whitelisted REST endpoints consumed by the Next.js frontend.

All calculations happen on the backend; the frontend only reads/writes data and
triggers these endpoints. Phase 1 declares the surface; logic lands in Phase 2.
"""

import frappe


@frappe.whitelist()
def calculate_active_salary(profile, period_date):
	"""Trigger the payroll engine for one employee profile."""
	raise NotImplementedError("Phase 2: wire to services.payroll_engine.engine")


@frappe.whitelist()
def evaluate_increment(profile):
	"""Preview the annual increment for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.increment.increment_service")


@frappe.whitelist()
def evaluate_promotion(profile):
	"""Preview a promotion for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.promotion.promotion_service")


@frappe.whitelist()
def compute_pension(profile, calculation_date):
	"""Compute the pension for an employee profile."""
	raise NotImplementedError("Phase 2: wire to services.pension.pension_service")
