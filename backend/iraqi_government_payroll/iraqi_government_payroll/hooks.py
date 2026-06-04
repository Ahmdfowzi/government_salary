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
# Roles are shipped as a fixture so RBAC is reproducible across sites.
fixtures = [
	{"dt": "Role", "filters": [["role_name", "in", [
		"Payroll Administrator",
		"Payroll Manager",
		"Payroll Officer",
		"HR User",
		"Finance User",
		"Auditor",
	]]]},
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
