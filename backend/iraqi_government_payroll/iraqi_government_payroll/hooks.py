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
		"Government Payroll Administrator",
		"Payroll Manager",
		"Payroll Officer",
		"HR User",
		"HR Officer",
		"Finance User",
		"Finance Officer",
		"Auditor",
		"Read Only User",
	]]]},
	"Government Grade",
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

# Document Events
# -------------------------
# Historical integrity (Phase 3 M3): reject lifecycle/transaction events dated
# inside a LOCKED payroll period for the employee (retroactive protection).
_GUARD = "iraqi_government_payroll.services.historical.history_service.guard_retroactive_change"
doc_events = {
	"Promotion Request": {"validate": _GUARD},
	"Employee Transfer": {"validate": _GUARD},
	"Employee Retirement": {"validate": _GUARD},
}

# Scheduled Tasks (Phase 2)
# -------------------------
# e.g. flag employees due for increment/promotion.
# scheduler_events = {}
