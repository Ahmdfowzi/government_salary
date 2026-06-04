# Copyright (c) 2026, Iraqi Government Payroll
"""Payroll Run batch engine (M7) — pure Python, no Frappe.

Iterates eligible employee profiles, computes each salary via the M5 Net Salary
Orchestrator, and upserts a DRAFT Salary Slip through an injected slip store
(idempotent — re-running updates the existing draft instead of duplicating).
M7 does NOT submit slips, so no snapshots are written for draft calculations.
Increment/promotion are NOT recalculated here — profiles are consumed as-is.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional

from .engine import EmployeeInput
from .net_salary import compute_net_salary
from .scale_resolver import resolve_grade_code

STATUS_DRAFT = "Draft"
STATUS_PROCESSING = "Processing"
STATUS_COMPLETED = "Completed"
STATUS_COMPLETED_WITH_WARNINGS = "Completed With Warnings"
STATUS_FAILED = "Failed"


@dataclass
class SlipOutcome:
	employee_profile: str
	slip_id: Optional[str]
	created: bool
	net_salary: Optional[int]
	warnings: List[str] = field(default_factory=list)
	provisional_flags: List[str] = field(default_factory=list)
	error: Optional[str] = None


@dataclass
class PayrollRunResult:
	status: str
	total_employees: int
	processed_count: int
	success_count: int
	warning_count: int
	error_count: int
	outcomes: List[SlipOutcome] = field(default_factory=list)
	error_log: List[str] = field(default_factory=list)

	def to_dict(self):
		return asdict(self)


def employee_input_from_profile(profile, period_date):
	return EmployeeInput(
		grade_code=resolve_grade_code(profile.get("grade_code"), profile.get("current_grade")),
		stage=profile.get("current_stage"),
		period_date=str(period_date),
		qualification=profile.get("qualification"),
		position_allowance_category=profile.get("position_allowance_category"),
		risk_applicable=bool(profile.get("risk_allowance_applicable")),
		risk_category=profile.get("risk_category"),
		spouse_eligible=(profile.get("marital_status") == "Married"),
		children_count=profile.get("eligible_children_count") or 0,
	)


def run_payroll_batch(period_name, run_name, rule_set, profiles, ctx, slip_store, period_date):
	"""Process each profile -> upsert a draft Salary Slip. Returns PayrollRunResult.

	slip_store must implement upsert(period, run, employee, rule_set, result) -> (slip_id, created).
	"""
	total = len(profiles)
	processed = success = warning = error = 0
	outcomes, error_log = [], []

	for p in profiles:
		emp_id = p.get("name") or p.get("employee_number")
		try:
			emp = employee_input_from_profile(p, period_date)
			res = compute_net_salary(ctx, emp)
			slip_id, created = slip_store.upsert(period_name, run_name, emp_id, rule_set, res)
			processed += 1
			has_warnings = bool(res.warnings) or bool(res.provisional_flags)
			if has_warnings:
				warning += 1
			else:
				success += 1
			outcomes.append(SlipOutcome(
				employee_profile=emp_id, slip_id=slip_id, created=created,
				net_salary=res.net_salary, warnings=res.warnings,
				provisional_flags=res.provisional_flags))
		except Exception as exc:   # one bad employee must not abort the batch
			error += 1
			error_log.append(f"{emp_id}: {exc}")
			outcomes.append(SlipOutcome(employee_profile=emp_id, slip_id=None, created=False,
										net_salary=None, error=str(exc)))

	if total > 0 and error == total:
		status = STATUS_FAILED
	elif error > 0 or warning > 0:
		status = STATUS_COMPLETED_WITH_WARNINGS
	else:
		status = STATUS_COMPLETED

	return PayrollRunResult(
		status=status, total_employees=total, processed_count=processed,
		success_count=success, warning_count=warning, error_count=error,
		outcomes=outcomes, error_log=error_log)
