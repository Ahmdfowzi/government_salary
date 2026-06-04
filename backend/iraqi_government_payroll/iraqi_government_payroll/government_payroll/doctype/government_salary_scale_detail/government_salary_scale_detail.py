# Copyright (c) 2026, Iraqi Government Payroll
# For license information, please see license.txt
"""Government Salary Scale Detail — child row of :class:`Government Salary Scale`.

Purpose
-------
One row of the grade/stage matrix: the stored basic salary for a given
(grade, stage). The engine READS this table — it does not compute the scale by
formula (per the analysis: rely on the stored official table).

Validation rules (Phase 2)
--------------------------
V1. (grade, stage) must be unique within a parent scale.
V2. basic_salary must be > 0.
V3. Consistency check: stage_n basic ≈ stage_1 + (n-1) * annual_increment.
"""

from frappe.model.document import Document


class GovernmentSalaryScaleDetail(Document):
	pass
