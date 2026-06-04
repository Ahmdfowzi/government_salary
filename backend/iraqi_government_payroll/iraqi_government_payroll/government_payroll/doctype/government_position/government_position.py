# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Position — master record for an organizational post.

Purpose
-------
Defines a position within a Government Entity: its grade band, whether it is
managerial, its authorized head count (for promotion vacancy checks) and the
keys used to match position/risk allowance rules. No business logic in M1.

Relationships
-------------
- many -> 1 :class:`Government Entity` (field ``government_entity``)
- referenced by :class:`Government Employee Payroll Profile`
"""

from frappe.model.document import Document


class GovernmentPosition(Document):
	pass
