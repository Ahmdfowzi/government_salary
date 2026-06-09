# Copyright (c) 2026, Iraqi Government Payroll
"""Pure builder for the Government Payroll Slip (مفردات راتب).

Assembles the print-ready slip from the immutable Payroll Calculation Snapshot
(the SOURCE OF TRUTH for every amount) plus employee / period / entity master
data. It NEVER recalculates payroll — it only re-presents and groups stored
amounts. No Frappe imports, so it is unit-testable on the host.

Inputs are plain dicts (the caller in api/slip_api wires them from Frappe docs):

    snapshot = {
        "grade_code": "7", "stage": 1,
        "gross_amount": 464000, "total_deductions": 5833, "net_amount": 458167,
        "output": {"basic_salary": 320000, ...},          # output_snapshot (JSON)
        "lines": [{"component_code","component_name","line_type","amount",
                   "basis_amount","rate"}, ...],           # Earning / Deduction
    }
    profile = {"employee_name","employee_number","national_id","appointment_date",
               "protected_salary_difference","last_promotion_date"}
    period  = {"month","year","end_date"}
    org     = {"entity_name","department_name"}
    meta    = {"list_sequence","payroll_date","payment_officer","payment_number",
               "leave_balance_annual","leave_balance_sick","total_rewards",
               "adjustment_amount","misc_deduction_lines","cash_rounding_step"}
"""

from datetime import date, datetime

from .component_labels import (
	arabic_component, display_value, MARITAL_AR, QUALIFICATION_AR,
)

# Smallest circulating Iraqi banknote — net pay is displayed rounded to this for
# cash disbursement. PRINT-ONLY: it never changes the engine's stored net amount.
DEFAULT_CASH_ROUNDING_STEP = 250

BASIC_CODES = {"BASIC", "BASIC_SALARY", "ACTIVE_BASIC"}


def _num(v):
	try:
		return float(v) if v not in (None, "") else 0.0
	except (TypeError, ValueError):
		return 0.0


def _parse_date(value):
	if isinstance(value, (date, datetime)):
		return value if isinstance(value, date) and not isinstance(value, datetime) else value.date()
	if not value:
		return None
	for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
		try:
			return datetime.strptime(str(value)[: len(fmt) + 2], fmt).date()
		except ValueError:
			continue
	try:
		return datetime.fromisoformat(str(value)).date()
	except ValueError:
		return None


def _years_between(start, end):
	s, e = _parse_date(start), _parse_date(end)
	if not s or not e:
		return 0
	years = e.year - s.year - (1 if (e.month, e.day) < (s.month, s.day) else 0)
	return max(0, years)


def _round_to(amount, step):
	step = int(step or 0)
	if step <= 0:
		return round(_num(amount))
	return int(round(_num(amount) / step)) * step


def build_slip(snapshot, profile=None, period=None, org=None, meta=None):
	"""Return a dict of Government Payroll Slip fields + the three line lists."""
	profile = profile or {}
	period = period or {}
	org = org or {}
	meta = meta or {}
	out = snapshot.get("output") or {}
	lines = snapshot.get("lines") or []

	# base salary: from the snapshot output (engine), falling back to any BASIC line
	base_salary = _num(out.get("basic_salary"))
	if not base_salary:
		base_salary = sum(
			_num(l.get("amount")) for l in lines
			if str(l.get("component_code", "")).upper() in BASIC_CODES)

	# allowance lines = Earning lines that are NOT the basic salary. The display
	# name is Arabic; the internal component_code is preserved unchanged.
	allowance_lines = []
	for l in lines:
		if l.get("line_type") != "Earning":
			continue
		code = l.get("component_code", "")
		if str(code).upper() in BASIC_CODES:
			continue
		allowance_lines.append({
			"component_code": code,
			"allowance_name": arabic_component(code, l.get("component_name")),
			"percentage": _num(l.get("rate")),
			"base_amount": _num(l.get("basis_amount")),
			"adjustment_amount": 0.0,
			"amount": _num(l.get("amount")),
		})

	# deduction lines = Deduction lines (Arabic display, internal code preserved)
	deduction_lines = [
		{"component_code": l.get("component_code", ""),
		 "deduction_name": arabic_component(l.get("component_code"), l.get("component_name")),
		 "amount": _num(l.get("amount"))}
		for l in lines if l.get("line_type") == "Deduction"
	]

	# misc deductions are print-only (no engine source) — supplied via meta
	misc_deduction_lines = [
		{"description": m.get("description"), "amount": _num(m.get("amount"))}
		for m in (meta.get("misc_deduction_lines") or [])
	]

	total_allowances = sum(a["amount"] for a in allowance_lines)
	total_misc_deductions = sum(m["amount"] for m in misc_deduction_lines)
	# Source of truth for deductions/net is the snapshot, NOT a re-sum.
	total_deductions = _num(snapshot.get("total_deductions"))
	net_pay = _num(snapshot.get("net_amount"))

	adjustment_amount = _num(meta.get("adjustment_amount")
							 if meta.get("adjustment_amount") is not None
							 else profile.get("protected_salary_difference"))
	total_rewards = _num(meta.get("total_rewards"))
	total_entitlement = base_salary + total_allowances + adjustment_amount + total_rewards

	rounding_step = meta.get("cash_rounding_step", DEFAULT_CASH_ROUNDING_STEP)

	payroll_date = meta.get("payroll_date") or period.get("end_date")
	# Promotion year: last promotion, else the date the current grade started.
	promo = _parse_date(profile.get("last_promotion_date")) \
		or _parse_date(profile.get("current_grade_date"))
	# Service: from appointment date, else the recorded service-start date.
	service_start = profile.get("appointment_date") or profile.get("retirement_service_start_date")

	return {
		# links / metadata
		"list_sequence": meta.get("list_sequence"),
		"payroll_date": payroll_date,
		"payment_officer": meta.get("payment_officer"),
		"payment_number": meta.get("payment_number"),
		# entity
		"entity_name": org.get("entity_name"),
		"department_name": org.get("department_name"),
		"position_title": org.get("position_title"),
		"payroll_month": period.get("month"),
		"payroll_year": period.get("year"),
		# employee
		"employee_name": profile.get("employee_name"),
		"employee_number": profile.get("employee_number"),
		"unified_national_id": profile.get("national_id"),
		# Arabic display values; internal stored option values are unchanged.
		"qualification": display_value(QUALIFICATION_AR, profile.get("qualification")),
		"marital_status": display_value(MARITAL_AR, profile.get("marital_status")),
		"appointment_date": profile.get("appointment_date"),
		"grade": str(snapshot.get("grade_code") or ""),
		"stage": snapshot.get("stage"),
		"promotion_year": promo.year if promo else (meta.get("promotion_year") or ""),
		"years_of_service": _years_between(service_start, payroll_date),
		# leave (print-only)
		"leave_balance_annual": meta.get("leave_balance_annual") or 0,
		"leave_balance_sick": meta.get("leave_balance_sick") or 0,
		# amounts
		"base_salary": base_salary,
		"adjustment_amount": adjustment_amount,
		"total_allowances": total_allowances,
		"total_rewards": total_rewards,
		"total_entitlement": total_entitlement,
		"total_deductions": total_deductions,
		"total_misc_deductions": total_misc_deductions,
		"net_pay": net_pay,
		"amount_before_rounding": net_pay,
		"amount_after_rounding": _round_to(net_pay, rounding_step),
		# lines
		"allowance_lines": allowance_lines,
		"deduction_lines": deduction_lines,
		"misc_deduction_lines": misc_deduction_lines,
	}
