"""Frappe app hooks for the Iraqi Government Payroll application."""

app_name = "iraqi_government_payroll"
app_title = "Iraqi Government Payroll"
app_publisher = "Iraqi Government Payroll"
app_description = "Production payroll system for Iraqi government employees (salary, increment, promotion, pension, tax)."
app_email = "support@example.gov.iq"
app_license = "MIT"

# Modules
# ------------------
# Declared in modules.txt: "Government Payroll"

# Fixtures
# ------------------
# Roles + the versioned legal rule set are shipped as fixtures so RBAC and the
# IRAQ-2015 rule package are reproducible across sites. Order matters on import:
# Government Rule Set must load before the rule members that link to it.
fixtures = [
	{"dt": "Role", "filters": [["role_name", "in", [
		"Payroll Administrator",
		"Payroll Manager",
		"Payroll Officer",
		"HR User",
		"Finance User",
		"Auditor",
	]]]},
	"Government Rule Set",
	"Government Salary Scale",
	"Qualification Appointment Rule",
	"Allowance Rule",
	"Income Tax Bracket",
	"Tax Allowance Rule",
	"Pension Rule",
	"Promotion Rule",
	"Annual Increment Rule",
	"Geographic Area",
	"Government Payroll Settings",
]

# Document Events (Phase 2)
# -------------------------
# Calculation side-effects (apply increment/promotion, write audit log) will be
# wired through controller methods / doc_events once the engines are implemented.
# doc_events = {}

# Scheduled Tasks (Phase 2)
# -------------------------
# e.g. flag employees due for increment/promotion.
# scheduler_events = {}
