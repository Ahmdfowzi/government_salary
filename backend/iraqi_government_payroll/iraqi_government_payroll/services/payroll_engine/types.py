# Copyright (c) 2026, Iraqi Government Payroll
"""Core engine value types — pure Python, no Frappe dependency (unit-testable)."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional

# Engine version is pinned into every Payroll Calculation Snapshot for reproducibility.
ENGINE_VERSION = "m3-active-salary-0.1.0"


class PayrollError(Exception):
	"""Raised on unrecoverable resolution errors (no/many rule sets, missing scale row)."""


@dataclass
class AllowanceLine:
	component_code: str
	component_name: str
	line_type: str          # "Earning" / "Deduction"
	match_key: str
	amount: float
	basis_amount: float
	rate: Optional[float] = None      # percent, for percentage components
	capped: bool = False              # subject to the 200% cap
	cap_applied: bool = False         # cap actually bound this line
	provisional: bool = False         # came from a confirmed=false rule
	source_rule: str = ""
	reason_text: str = ""


@dataclass
class CalculationResult:
	rule_set: str
	engine_version: str
	period_date: str
	grade_code: str
	stage: int
	basic_salary: float
	allowance_lines: List[AllowanceLine] = field(default_factory=list)
	capped_allowance_total: float = 0.0
	non_capped_allowance_total: float = 0.0
	cap_excluded_amount: float = 0.0
	gross_salary: float = 0.0
	warnings: List[str] = field(default_factory=list)
	provisional_flags: List[str] = field(default_factory=list)

	def to_dict(self) -> dict:
		return asdict(self)
