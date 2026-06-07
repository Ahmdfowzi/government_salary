# Copyright (c) 2026, Iraqi Government Payroll
"""Canonical export column specs for the payroll reports — single source of truth.

One spec per report: the ordered (key, header) columns, how to pull the row list
out of the aggregator's return value, and the totals-row values (if any). Used by
the Excel exporter (and reused by future PDF). NO aggregation happens here — specs
only describe how to lay out data the report functions already produced.
"""


def _rows(data):
	return data.get("rows", [])


def _summary_rows(data):
	# run_summary returns the totals object itself as the single row.
	return [data]


def _component_spec(title):
	"""Allowances / Deductions registers share the same column layout."""
	return {
		"title": title,
		"columns": [
			("employee_profile", "الموظف"),
			("employee_name", "الاسم"),
			("component_code", "الرمز"),
			("component_name", "المكوّن"),
			("basis_amount", "الأساس"),
			("rate", "النسبة"),
			("amount", "المبلغ"),
		],
		"rows": _rows,
		"totals": lambda d: {"amount": d["grand_total"]},
	}


REPORT_SPECS = {
	"run_summary": {
		"title": "ملخص الدورة",
		"columns": [
			("employees", "عدد الموظفين"),
			("total_basic", "الأساسي"),
			("total_earnings", "الاستحقاقات"),
			("total_deductions", "الاستقطاعات"),
			("total_net", "الصافي"),
		],
		"rows": _summary_rows,
		"totals": lambda d: {},
	},
	"employee_register": {
		"title": "كشف رواتب الموظفين",
		"columns": [
			("employee_profile", "الموظف"),
			("employee_name", "الاسم"),
			("grade_code", "الدرجة"),
			("stage", "المرحلة"),
			("basic", "الأساسي"),
			("allowances", "المخصصات"),
			("deductions", "الاستقطاعات"),
			("net", "الصافي"),
		],
		"rows": _rows,
		"totals": lambda d: dict(d["totals"]),
	},
	"allowances_register": _component_spec("كشف المخصصات"),
	"deductions_register": _component_spec("كشف الاستقطاعات"),
	"tax_register": {
		"title": "كشف الضريبة",
		"columns": [
			("employee_profile", "الموظف"),
			("employee_name", "الاسم"),
			("taxable", "الدخل الخاضع"),
			("tax", "الضريبة"),
		],
		"rows": _rows,
		"totals": lambda d: {"tax": d["total_tax"]},
	},
	"pension_register": {
		"title": "كشف التقاعد",
		"columns": [
			("employee_profile", "الموظف"),
			("employee_name", "الاسم"),
			("qualification", "التحصيل"),
			("service_years", "سنوات الخدمة"),
			("average_36_months", "متوسط ٣٦ شهر"),
			("approved_pension", "التقاعد المُقَرّ"),
			("certificate_allowance", "مخصص الشهادة"),
			("cost_of_living", "غلاء المعيشة"),
			("gross_pension", "الإجمالي"),
			("monthly_tax", "الضريبة الشهرية"),
			("other_deductions", "استقطاعات أخرى"),
			("net_pension", "الصافي"),
			("end_of_service_bonus", "مكافأة نهاية الخدمة"),
			("status", "الحالة"),
			("calculation_date", "تاريخ الاحتساب"),
		],
		"rows": _rows,
		"totals": lambda d: dict(d["totals"]),
	},
	"bank_transfer": {
		"title": "تحويل بنكي",
		"columns": [
			("employee_profile", "الموظف"),
			("employee_name", "الاسم"),
			("iban", "IBAN"),
			("bank_name", "المصرف"),
			("bank_account", "رقم الحساب"),
			("national_id", "الهوية"),
			("net", "الصافي"),
			("bank_complete", "مكتمل"),
			("missing", "النواقص"),
		],
		"rows": _rows,
		"totals": lambda d: {"net": d["total_net"]},
	},
}
