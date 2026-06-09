# Copyright (c) 2026, Iraqi Government Payroll
"""Pure tests for the Government Payroll Slip builder + print HTML.

No bench: build_slip re-presents a snapshot (source of truth) without touching the
engine, and build_slip_html renders the RTL Arabic layout. Run:
    python3 -m unittest test_slip -v
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, APP_ROOT)

from iraqi_government_payroll.services.slip.slip_builder import build_slip  # noqa: E402
from iraqi_government_payroll.services.reports.slip_pdf import build_slip_html  # noqa: E402


def sample_snapshot():
	return {
		"grade_code": "7", "stage": 1,
		"gross_amount": 464000, "total_deductions": 5833, "net_amount": 458167,
		"output": {"basic_salary": 320000},
		"lines": [
			{"component_code": "CERT_ACT_BACHELOR", "component_name": "Certificate Allowance",
			 "line_type": "Earning", "amount": 144000, "basis_amount": 320000, "rate": 45},
			{"component_code": "INCOME_TAX", "component_name": "Income Tax",
			 "line_type": "Deduction", "amount": 5833, "basis_amount": 0, "rate": 0},
		],
	}


PROFILE = {
	"employee_name": "موظف تجريبي", "employee_number": "E1",
	"national_id": "199000000001", "appointment_date": "2010-01-15",
	"protected_salary_difference": 0, "last_promotion_date": "2018-06-01",
}
PERIOD = {"month": 6, "year": 2020, "end_date": "2020-06-30"}
ORG = {"entity_name": "وزارة العرض", "department_name": "قسم الرواتب"}


def built(meta=None):
	return build_slip(sample_snapshot(), profile=PROFILE, period=PERIOD, org=ORG,
					  meta=meta or {"list_sequence": 3})


class TestBuildSlip(unittest.TestCase):
	def test_base_salary_separated_from_allowances(self):
		s = built()
		self.assertEqual(s["base_salary"], 320000)
		self.assertEqual(len(s["allowance_lines"]), 1)        # basic is NOT a line
		a = s["allowance_lines"][0]
		self.assertEqual(a["amount"], 144000)
		self.assertEqual(a["percentage"], 45)
		self.assertEqual(a["base_amount"], 320000)

	def test_deduction_lines(self):
		s = built()
		self.assertEqual(len(s["deduction_lines"]), 1)
		self.assertEqual(s["deduction_lines"][0]["amount"], 5833)
		self.assertEqual(s["deduction_lines"][0]["deduction_name"], "Income Tax")

	def test_totals_from_snapshot_not_recomputed(self):
		s = built()
		self.assertEqual(s["total_allowances"], 144000)
		self.assertEqual(s["total_entitlement"], 464000)     # base + allowances
		self.assertEqual(s["total_deductions"], 5833)        # snapshot value (source of truth)
		self.assertEqual(s["net_pay"], 458167)               # snapshot net, never recomputed

	def test_cash_rounding_is_print_only(self):
		s = built()
		self.assertEqual(s["amount_before_rounding"], 458167)
		self.assertEqual(s["amount_after_rounding"], 458250)  # nearest 250 IQD
		# default rounding never alters the authoritative net
		self.assertEqual(s["net_pay"], 458167)

	def test_identity_and_service(self):
		s = built()
		self.assertEqual(s["grade"], "7")
		self.assertEqual(s["stage"], 1)
		self.assertEqual(s["employee_number"], "E1")
		self.assertEqual(s["unified_national_id"], "199000000001")
		self.assertEqual(s["payroll_month"], 6)
		self.assertEqual(s["payroll_year"], 2020)
		self.assertEqual(s["years_of_service"], 10)           # 2010-01 -> 2020-06
		self.assertEqual(s["promotion_year"], 2018)
		self.assertEqual(s["list_sequence"], 3)

	def test_misc_deductions_print_only(self):
		s = built({"misc_deduction_lines": [{"description": "سلفة", "amount": 25000}]})
		self.assertEqual(len(s["misc_deduction_lines"]), 1)
		self.assertEqual(s["total_misc_deductions"], 25000)
		# misc + rewards are print-only; engine net is unchanged
		self.assertEqual(s["net_pay"], 458167)

	def test_no_deductions_safe(self):
		snap = sample_snapshot()
		snap["lines"] = [l for l in snap["lines"] if l["line_type"] != "Deduction"]
		snap["total_deductions"] = 0
		snap["net_amount"] = 464000
		s = build_slip(snap, profile=PROFILE, period=PERIOD, org=ORG)
		self.assertEqual(s["deduction_lines"], [])
		self.assertEqual(s["net_pay"], 464000)


class TestSlipHtml(unittest.TestCase):
	def test_rtl_arabic_layout_with_font_and_values(self):
		html = build_slip_html(built())
		self.assertIn('dir="rtl"', html)
		self.assertIn("@font-face", html)
		for label in ("مفردات راتب", "الاستحقاقات", "الاستقطاعات", "صافي الراتب",
					  "الرقم الوطني الموحد", "سنوات الخدمة"):
			self.assertIn(label, html)
		# English numerals with separators, including the rounded amount
		self.assertIn("320,000", html)
		self.assertIn("458,167", html)
		self.assertIn("458,250", html)


if __name__ == "__main__":
	unittest.main()
