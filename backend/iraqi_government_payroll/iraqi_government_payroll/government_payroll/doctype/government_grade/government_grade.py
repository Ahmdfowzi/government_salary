# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Grade — master list of salary grades (Phase 5 M4.1).

The record name IS the canonical grade code ("7", "SPECIAL_A", …), so a Link to
this DocType stores exactly the string the legacy `grade_code` Select used and the
payroll engine keeps resolving salaries unchanged. The legal source of valid
(grade, stage) combinations and basic salary remains the Government Salary Scale.
"""

from frappe.model.document import Document


class GovernmentGrade(Document):
	pass
