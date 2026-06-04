# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Entity — the organizational hierarchy (NestedSet tree).

Purpose
-------
A single self-referential tree representing the full government org structure:
Ministry -> Authority/Governorate -> Directorate -> Department -> Division ->
Unit. Employee profiles link to an entity (usually a leaf), enabling org-wide
rollups (department/cost-center reports) via nested-set queries.

Hierarchy validation
---------------------
``ALLOWED_PARENTS`` defines, per entity type, which parent types are legal.
A ``None`` entry means the type may sit at the top of the tree.
"""

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet

# Allowed parent entity_type per child entity_type. None = may be a root node.
ALLOWED_PARENTS = {
	"Ministry": [None],
	"Authority": [None, "Ministry"],
	"Governorate": [None, "Ministry"],
	"Directorate": ["Ministry", "Authority", "Governorate"],
	"Department": ["Ministry", "Authority", "Governorate", "Directorate"],
	"Division": ["Directorate", "Department"],
	"Unit": ["Department", "Division"],
}


class GovernmentEntity(NestedSet):
	nsm_parent_field = "parent_government_entity"

	def validate(self):
		self.validate_hierarchy()

	def validate_hierarchy(self):
		"""Enforce that this entity's parent type is legal for its own type."""
		allowed = ALLOWED_PARENTS.get(self.entity_type)
		if allowed is None:
			frappe.throw(_("Unknown entity type: {0}").format(self.entity_type))

		parent_type = None
		if self.parent_government_entity:
			parent_type = frappe.db.get_value(
				"Government Entity", self.parent_government_entity, "entity_type"
			)

		if parent_type not in allowed:
			if parent_type is None:
				frappe.throw(
					_("{0} cannot be a top-level entity; it requires a parent of type: {1}").format(
						self.entity_type, ", ".join(t for t in allowed if t)
					)
				)
			frappe.throw(
				_("A {0} cannot be placed under a {1}. Allowed parents: {2}").format(
					self.entity_type, parent_type, ", ".join(str(t) for t in allowed)
				)
			)
