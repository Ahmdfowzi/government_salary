# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Rule Set Parameter — child of :class:`Government Rule Set`.

A single versioned legal knob (the PC-x configurables): pension contribution
rate, geographic-in-cap flag, cost-of-living method, overtime formula, etc.
Stored per rule set so parameters version with the legal package.
"""

from frappe.model.document import Document


class RuleSetParameter(Document):
	pass
