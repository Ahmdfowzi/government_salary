# Copyright (c) 2026, Iraqi Government Payroll
"""Pure Family & Dependents logic — age, eligibility, and summary counts.

No Frappe, no money: this computes WHO counts (ages, eligibility flags, counts)
from the dependent records and a CONFIG of age/income thresholds. The actual
allowance / tax amounts are NOT here — they stay in the configurable Allowance
Rule / Tax Rule fixtures the engine reads. The eligibility thresholds are passed
in (the controller loads them from Government Payroll Settings) so no legal value
is hard-coded in the engine path.

`summarize(members, as_of, config)` returns the enriched members (each with a
computed `age` and `eligible_for_family_allowance`) plus the summary counts the
employee profile stores and the payroll snapshot records.
"""

from datetime import date, datetime

# Neutral defaults — overridden by Government Payroll Settings (configurable).
DEFAULT_CONFIG = {
	"child_max_age": 18,            # children eligible up to this age...
	"student_max_age": 24,         # ...or this age while a full-time student
	"dependent_income_threshold": 0,  # own income above this -> self-supporting
}

CHILD_RELATIONS = ("Son", "Daughter")


def _parse_date(value):
	if isinstance(value, datetime):
		return value.date()
	if isinstance(value, date):
		return value
	if not value:
		return None
	try:
		return datetime.fromisoformat(str(value)[:10]).date()
	except ValueError:
		return None


def _num(v):
	try:
		return float(v) if v not in (None, "") else 0.0
	except (TypeError, ValueError):
		return 0.0


def _truthy(v, default=False):
	if v is None or v == "":
		return default
	if isinstance(v, str):
		return v.strip().lower() not in ("0", "false", "no", "")
	return bool(v)


def compute_age(date_of_birth, as_of=None):
	"""Whole years between date_of_birth and as_of (defaults to today). None-safe."""
	born = _parse_date(date_of_birth)
	ref = _parse_date(as_of) or date.today()
	if not born:
		return None
	return max(0, ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day)))


def _is_self_supporting(member, config):
	"""Employed dependent earning above the threshold — excluded from eligibility."""
	employed = _truthy(member.get("is_employed")) or \
		str(member.get("employment_type") or "None") not in ("None", "")
	return employed and _num(member.get("monthly_income")) > config["dependent_income_threshold"]


def evaluate_eligibility(member, age, config):
	"""Is this dependent eligible for the family allowance? Pure predicate."""
	if not _truthy(member.get("is_alive"), default=True):
		return False
	if not _truthy(member.get("financially_dependent"), default=True):
		return False
	if _is_self_supporting(member, config):           # employed-dependent exclusion
		return False
	if _truthy(member.get("has_disability")):          # disability: eligible regardless of age
		return True
	if member.get("relation") in CHILD_RELATIONS:
		if age is None:
			return False
		if age <= config["child_max_age"]:
			return True
		return bool(_truthy(member.get("is_student")) and age <= config["student_max_age"])
	# Spouse / parents / other dependents: eligible while alive + financially dependent.
	return True


def summarize(members, as_of=None, config=None):
	"""Return {'members': [...enriched...], 'summary': {...counts...}}.

	Each enriched member gains a computed ``age`` and ``eligible_for_family_allowance``.
	Counts: spouse_count, children_count, eligible_children_count, dependents_count,
	eligible_dependents_count, disabled_dependents_count, employed_dependents_count,
	student_dependents_count.
	"""
	cfg = {**DEFAULT_CONFIG, **(config or {})}
	enriched = []
	c = dict(spouse_count=0, children_count=0, eligible_children_count=0,
			 dependents_count=0, eligible_dependents_count=0,
			 disabled_dependents_count=0, employed_dependents_count=0,
			 student_dependents_count=0)

	for m in members or []:
		age = compute_age(m.get("date_of_birth"), as_of)
		alive = _truthy(m.get("is_alive"), default=True)
		rel = m.get("relation")
		eligible = evaluate_eligibility(m, age, cfg)
		is_child = rel in CHILD_RELATIONS

		if rel == "Spouse" and alive:
			c["spouse_count"] += 1
		if is_child:
			c["children_count"] += 1
		if is_child and eligible:
			c["eligible_children_count"] += 1
		if alive and _truthy(m.get("financially_dependent"), default=True):
			c["dependents_count"] += 1
		if eligible:
			c["eligible_dependents_count"] += 1
		if _truthy(m.get("has_disability")):
			c["disabled_dependents_count"] += 1
		if _truthy(m.get("is_employed")):
			c["employed_dependents_count"] += 1
		if _truthy(m.get("is_student")):
			c["student_dependents_count"] += 1

		enriched.append({**m, "age": age,
						 "eligible_for_family_allowance": 1 if eligible else 0})

	return {"members": enriched, "summary": c}
