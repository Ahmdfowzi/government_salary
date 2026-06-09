# Copyright (c) 2026, Iraqi Government Payroll
"""Arabic DISPLAY names for payroll components on the printable slip.

Internal identifiers (component_code) are NEVER changed — this only maps a code to
an Arabic label for printing. Matching is by code prefix so it covers every
qualification / position / family / deduction variant without listing each one.
"""

# Exact-code overrides first, then prefix rules.
_EXACT = {
	"FAM_SPOUSE": "مخصصات الزوجية",
	"FAM_CHILD": "مخصصات الأطفال",
	"INCOME_TAX": "ضريبة الدخل",
	"DED_TAX": "ضريبة الدخل",
	"DED_PENSION": "التوقيفات التقاعدية",
	"PENSION_DEDUCTION": "التوقيفات التقاعدية",
	"DED_ABSENCE": "استقطاع الغياب",
	"DED_PENALTY": "استقطاع العقوبات",
	"DED_LOAN": "استقطاع السلف والقروض",
	"DED_STAMPS": "الطوابع والاستقطاعات الأخرى",
	"OVERTIME_DEFAULT": "الأجور الإضافية",
}

# (prefix, arabic) — first match wins.
_PREFIXES = (
	("CERT_ACT", "مخصصات الشهادة"),
	("CERT_PEN", "مخصصات الشهادة"),
	("CERT", "مخصصات الشهادة"),
	("CRAFT", "مخصصات المهنة"),
	("POS", "مخصصات المنصب"),
	("RISK", "مخصصات الخطورة"),
	("FAM", "المخصصات العائلية"),
	("OVERTIME", "الأجور الإضافية"),
	("TAX", "ضريبة الدخل"),
	("PENSION", "التوقيفات التقاعدية"),
)

BASIC_SALARY_AR = "الراتب الاسمي"


def arabic_component(code, fallback=None):
	"""Arabic display label for a component_code; falls back to the given name."""
	if not code:
		return fallback or ""
	c = str(code).upper()
	if c in _EXACT:
		return _EXACT[c]
	for prefix, label in _PREFIXES:
		if c.startswith(prefix):
			return label
	return fallback or str(code)
