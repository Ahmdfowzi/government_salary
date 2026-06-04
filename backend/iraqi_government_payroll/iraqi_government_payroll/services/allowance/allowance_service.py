# Copyright (c) 2026, Iraqi Government Payroll
"""Core Allowance Resolver + 200% cap (M3).

Implements ONLY the active-salary earning allowances:
  - Certificate active allowance (match_key="Qualification")
  - Craft allowance (same mechanism, qualification "Trade / Craft")
  - Position allowance (match_key="Position Allowance Category")
  - Risk allowance (match_key="Risk Category") — only if configured on the employee
  - Family allowance (match_key="Family") — spouse / children, only if configured

Deliberately excluded in M3: overtime, deductions, pension contribution, income
tax, and Pension Certificate (pension context).

confirmed=false behaviour:
  - value present -> compute and mark provisional
  - value empty   -> skip and warn (never substitute zero silently)
Certificate no-match -> allowance 0 + note (no error).
"""

from ..payroll_engine.types import AllowanceLine

ACTIVE_CTX = ("Active", "Both")

# 200% cap (D1/D2 legal source: "مجموع المخصصات الخاضعة للسقف لا يجوز أن يتجاوز
# 200% من الراتب الاسمي" — the sum of CAPPED allowances may not exceed 200% of
# basic salary). Therefore:
#   * cap base               = basic salary
#   * max total CAPPED allowances allowed = 200% of basic salary = 2 x basic
#   * basic salary itself is NOT subject to the cap
# Implementation is intentionally kept at 2 x basic (CAP_MULTIPLIER = 2.0).
CAP_MULTIPLIER = 2.0


def _value_of(rule):
	if rule.get("calculation_type") == "Percentage":
		return rule.get("percentage")
	return rule.get("fixed_amount")


def _is_empty(v):
	return v is None or v == ""


def _is_capped(rule):
	return rule.get("capped_under_200") == "Yes"


def _make_line(rule, basic, warnings, provisional, count=1, extra_reason=""):
	"""Build one AllowanceLine honoring confirmed/empty rules. Returns None if skipped."""
	code = rule.get("component_code")
	v = _value_of(rule)
	confirmed = bool(rule.get("confirmed"))

	if _is_empty(v):
		if not confirmed:
			warnings.append(f"{code}: skipped — provisional value not set (confirmed=false, empty).")
		else:
			warnings.append(f"{code}: skipped — no value configured.")
		return None

	if rule.get("calculation_type") == "Percentage":
		rate = float(v)
		amount = round(basic * rate / 100.0, 2)
		basis = float(basic)
	else:
		rate = None
		amount = round(float(v) * count, 2)
		basis = 0.0

	reason = rule.get("source_reference", "") or ""
	if extra_reason:
		reason = (reason + " | " + extra_reason).strip(" |")

	line = AllowanceLine(
		component_code=code,
		component_name=rule.get("component_name", ""),
		line_type=rule.get("allowance_type", "Earning"),
		match_key=rule.get("match_key", ""),
		amount=amount,
		basis_amount=basis,
		rate=rate,
		capped=_is_capped(rule),
		provisional=(not confirmed),
		source_rule=f"{rule.get('rule_set')}/{code}",
		reason_text=reason,
	)
	if not confirmed:
		provisional.append(code)
	return line


def _find(rules, match_key, match_value):
	for r in rules:
		if (r.get("match_key") == match_key and r.get("match_value") == match_value
				and r.get("context") in ACTIVE_CTX):
			return r
	return None


def _find_any(rules, match_key):
	for r in rules:
		if r.get("match_key") == match_key and r.get("context") in ACTIVE_CTX:
			return r
	return None


def resolve_active_allowances(rules, emp, basic):
	"""Return (lines, warnings, provisional_flags) for the active-salary components."""
	warnings, provisional, lines = [], [], []

	# 1) Certificate active (and craft via qualification "Trade / Craft")
	if getattr(emp, "qualification", None):
		cert = _find(rules, "Qualification", emp.qualification)
		if cert is None:
			warnings.append(
				f"No certificate/craft allowance for qualification '{emp.qualification}' — allowance = 0.")
		else:
			ln = _make_line(cert, basic, warnings, provisional)
			if ln:
				lines.append(ln)
	else:
		warnings.append("No qualification on employee — certificate allowance = 0.")

	# 2) Position allowance
	cat = getattr(emp, "position_allowance_category", None)
	if cat:
		pos = _find(rules, "Position Allowance Category", cat)
		if pos is None:
			warnings.append(f"No position allowance for category '{cat}' — allowance = 0.")
		else:
			ln = _make_line(pos, basic, warnings, provisional)
			if ln:
				lines.append(ln)

	# 3) Risk allowance — only if configured on the employee
	if getattr(emp, "risk_applicable", False) and getattr(emp, "risk_category", None):
		risk = _find(rules, "Risk Category", emp.risk_category) or _find_any(rules, "Risk Category")
		if risk is None:
			warnings.append(f"Risk allowance configured but no rule for '{emp.risk_category}'.")
		else:
			ln = _make_line(risk, basic, warnings, provisional)
			if ln:
				lines.append(ln)

	# 4) Family allowance — only if configured
	if getattr(emp, "spouse_eligible", False):
		sp = _find(rules, "Family", "Spouse")
		if sp:
			ln = _make_line(sp, basic, warnings, provisional)
			if ln:
				lines.append(ln)
	children = int(getattr(emp, "children_count", 0) or 0)
	if children > 0:
		ch = _find(rules, "Family", "Child")
		if ch:
			n = min(children, 4)
			ln = _make_line(ch, basic, warnings, provisional, count=n,
							extra_reason=f"children={n} (max 4)")
			if ln:
				lines.append(ln)

	return lines, warnings, provisional


def apply_200_cap(lines, basic):
	"""Apply the 200%-of-basic cap to capped allowance lines.

	200% cap interpretation (implemented): the sum of capped allowances may not
	exceed 200% of basic salary (max = 2 x basic). Basic salary is the cap base
	and is not itself capped. When the cap binds, the allowed capped total is
	clamped to 2 x basic and the remainder is reported as ``excluded_amount``.

	Returns (allowed_capped_total, non_capped_total, excluded_amount, warnings).
	Marks cap_applied=True on capped lines when the cap binds.
	"""
	capped = [l for l in lines if l.capped]
	non_capped = [l for l in lines if not l.capped]
	sum_capped = round(sum(l.amount for l in capped), 2)
	sum_non = round(sum(l.amount for l in non_capped), 2)
	max_capped = round(basic * CAP_MULTIPLIER, 2)

	excluded = 0.0
	warnings = []
	if sum_capped > max_capped:
		excluded = round(sum_capped - max_capped, 2)
		for l in capped:
			l.cap_applied = True
		allowed = max_capped
		warnings.append(
			f"200% cap applied: capped allowances {sum_capped} exceed max {max_capped} "
			f"(200% of basic {basic}); excluded {excluded}.")
	else:
		allowed = sum_capped

	return allowed, sum_non, excluded, warnings
