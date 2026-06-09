# Copyright (c) 2026, Iraqi Government Payroll
"""Render a Government Payroll Slip to printable RTL Arabic HTML / PDF.

* ``build_slip_html(slip)`` — PURE: builds the مفردات راتب layout (RTL, Cairo font
  embedded as base64 @font-face, English numerals). No Frappe, so it is testable
  without a bench. It only presents the values the slip already holds.
* ``render_slip_pdf(html)`` — thin wrapper over wkhtmltopdf (Portrait A4).

Font: the bundled open-source **Cairo** (OFL) is used for both Arabic shaping and
English numerals; if it is missing, it falls back to the bundled **Amiri**.
"""

import base64
import os
from html import escape

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_CAIRO = os.path.join(_FONTS_DIR, "Cairo-Regular.ttf")
_AMIRI = os.path.join(_FONTS_DIR, "Amiri-Regular.ttf")

_font_cache = None


def _font():
	"""(family_name, data_uri) for the slip font — Cairo, else Amiri."""
	global _font_cache
	if _font_cache is None:
		path, family = (_CAIRO, "Cairo") if os.path.exists(_CAIRO) else (_AMIRI, "Amiri")
		with open(path, "rb") as fh:
			b64 = base64.b64encode(fh.read()).decode("ascii")
		_font_cache = (family, "data:font/truetype;base64," + b64)
	return _font_cache


def _money(v):
	"""English-numeral integer dinars with thousands separators."""
	try:
		return f"{int(round(float(v))):,}"
	except (TypeError, ValueError):
		return "0"


def _txt(v):
	return escape("" if v in (None, "") else str(v))


def _pct(v):
	try:
		f = float(v)
	except (TypeError, ValueError):
		return ""
	if not f:
		return ""
	return (f"{f:g}") + "%"


def _info(label, value):
	return f'<div class="cell"><span class="lbl">{escape(label)}</span>' \
		   f'<span class="val">{_txt(value)}</span></div>'


def build_slip_html(slip):
	"""Return a complete one-page RTL Arabic payroll-slip HTML document. Pure."""
	family, uri = _font()
	s = slip

	# ---- allowance (entitlement) rows: base salary first, then allowances ----
	ent_rows = [
		'<tr><td class="r">الراتب الاسمي</td><td></td><td></td><td></td>'
		f'<td class="n">{_money(s.get("base_salary"))}</td></tr>'
	]
	for a in s.get("allowance_lines") or []:
		ent_rows.append(
			"<tr>"
			f'<td class="r">{_txt(a.get("allowance_name"))}</td>'
			f'<td class="n">{_pct(a.get("percentage"))}</td>'
			f'<td class="n">{_money(a.get("base_amount")) if a.get("base_amount") else ""}</td>'
			f'<td class="n">{_money(a.get("adjustment_amount")) if a.get("adjustment_amount") else ""}</td>'
			f'<td class="n">{_money(a.get("amount"))}</td>'
			"</tr>"
		)
	if s.get("adjustment_amount"):
		ent_rows.append(
			f'<tr><td class="r">التعديل</td><td></td><td></td><td></td>'
			f'<td class="n">{_money(s.get("adjustment_amount"))}</td></tr>')
	if s.get("total_rewards"):
		ent_rows.append(
			f'<tr><td class="r">المكافآت</td><td></td><td></td><td></td>'
			f'<td class="n">{_money(s.get("total_rewards"))}</td></tr>')

	# ---- deduction rows + misc ----
	ded_rows = []
	for d in s.get("deduction_lines") or []:
		ded_rows.append(
			f'<tr><td class="r">{_txt(d.get("deduction_name"))}</td>'
			f'<td class="n">{_money(d.get("amount"))}</td></tr>')
	for m in s.get("misc_deduction_lines") or []:
		ded_rows.append(
			f'<tr><td class="r">{_txt(m.get("description"))} (متنوعة)</td>'
			f'<td class="n">{_money(m.get("amount"))}</td></tr>')
	if not ded_rows:
		ded_rows.append('<tr><td class="r">لا توجد استقطاعات</td><td class="n">0</td></tr>')

	html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
@font-face{{font-family:"SlipFont";src:url({uri}) format("truetype");}}
*{{font-family:"SlipFont","{family}",sans-serif;box-sizing:border-box;}}
body{{direction:rtl;color:#0f172a;font-size:11px;margin:0;padding:14px;}}
.title{{text-align:center;font-size:18px;font-weight:bold;margin-bottom:2px;}}
.sub{{text-align:center;font-size:12px;color:#334155;margin-bottom:10px;}}
.meta,.emp{{width:100%;border-collapse:collapse;margin-bottom:8px;}}
.meta td,.emp td{{border:1px solid #cbd5e1;padding:4px 6px;}}
.meta .k,.emp .k{{background:#f1f5f9;font-weight:bold;white-space:nowrap;width:1%;}}
.n{{direction:ltr;unicode-bidi:embed;text-align:left;}}
/* wkhtmltopdf (old WebKit) has no flexbox — use a table for the two columns. */
table.cols{{width:100%;border-collapse:separate;border-spacing:6px 0;}}
table.cols>tbody>tr>td.col{{vertical-align:top;width:50%;}}
.col h3{{margin:0 0 4px;font-size:12px;background:#0f172a;color:#fff;padding:4px 6px;}}
table.body{{width:100%;border-collapse:collapse;}}
table.body th,table.body td{{border:1px solid #94a3b8;padding:4px 6px;text-align:right;}}
table.body thead th{{background:#e2e8f0;font-weight:bold;}}
table.body td.n,table.body th.n{{text-align:left;direction:ltr;}}
tfoot td{{font-weight:bold;background:#f8fafc;}}
.totals{{width:100%;border-collapse:collapse;margin-top:10px;}}
.totals td{{border:1px solid #94a3b8;padding:6px 8px;}}
.totals .k{{background:#f1f5f9;font-weight:bold;}}
.totals .net{{background:#dcfce7;font-weight:bold;font-size:13px;}}
table.sign{{width:100%;margin-top:30px;border-collapse:separate;border-spacing:10px 0;}}
table.sign td{{text-align:center;width:25%;border-top:1px solid #94a3b8;padding-top:4px;font-size:11px;color:#334155;}}
</style></head><body>

<div class="title">مفردات راتب موظف</div>
<div class="sub">{_txt(s.get('entity_name'))}{(' — ' + _txt(s.get('department_name'))) if s.get('department_name') else ''}</div>

<table class="meta"><tbody><tr>
  <td class="k">التسلسل</td><td class="n">{_txt(s.get('list_sequence'))}</td>
  <td class="k">التاريخ</td><td class="n">{_txt(s.get('payroll_date'))}</td>
  <td class="k">الشهر / السنة</td><td class="n">{_txt(s.get('payroll_month'))} / {_txt(s.get('payroll_year'))}</td>
  <td class="k">أمين الصرف</td><td>{_txt(s.get('payment_officer'))}</td>
  <td class="k">رقم أمر الصرف</td><td class="n">{_txt(s.get('payment_number'))}</td>
</tr></tbody></table>

<table class="emp"><tbody>
<tr>
  <td class="k">الاسم</td><td>{_txt(s.get('employee_name'))}</td>
  <td class="k">الرقم الوظيفي</td><td class="n">{_txt(s.get('employee_number'))}</td>
  <td class="k">الرقم الوطني الموحد</td><td class="n">{_txt(s.get('unified_national_id'))}</td>
</tr>
<tr>
  <td class="k">الدرجة</td><td class="n">{_txt(s.get('grade'))}</td>
  <td class="k">المرحلة</td><td class="n">{_txt(s.get('stage'))}</td>
  <td class="k">سنة الترقية</td><td class="n">{_txt(s.get('promotion_year'))}</td>
</tr>
<tr>
  <td class="k">سنوات الخدمة</td><td class="n">{_txt(s.get('years_of_service'))}</td>
  <td class="k">رصيد الإجازة الاعتيادية</td><td class="n">{_txt(s.get('leave_balance_annual'))}</td>
  <td class="k">رصيد الإجازة المرضية</td><td class="n">{_txt(s.get('leave_balance_sick'))}</td>
</tr>
</tbody></table>

<table class="cols"><tbody><tr>
  <td class="col">
    <h3>الاستحقاقات</h3>
    <table class="body">
      <thead><tr><th>البيان</th><th class="n">النسبة</th><th class="n">الأساس</th><th class="n">التعديل</th><th class="n">المبلغ</th></tr></thead>
      <tbody>{''.join(ent_rows)}</tbody>
      <tfoot><tr><td colspan="4" class="r">مجموع الاستحقاق</td><td class="n">{_money(s.get('total_entitlement'))}</td></tr></tfoot>
    </table>
  </td>
  <td class="col">
    <h3>الاستقطاعات</h3>
    <table class="body">
      <thead><tr><th>البيان</th><th class="n">المبلغ</th></tr></thead>
      <tbody>{''.join(ded_rows)}</tbody>
      <tfoot>
        <tr><td class="r">مجموع الاستقطاعات المتنوعة</td><td class="n">{_money(s.get('total_misc_deductions'))}</td></tr>
        <tr><td class="r">مجموع الاستقطاعات</td><td class="n">{_money(s.get('total_deductions'))}</td></tr>
      </tfoot>
    </table>
  </td>
</tr></tbody></table>

<table class="totals"><tbody>
<tr>
  <td class="k">مجموع الاستحقاق</td><td class="n">{_money(s.get('total_entitlement'))}</td>
  <td class="k">مجموع الاستقطاعات</td><td class="n">{_money(s.get('total_deductions'))}</td>
  <td class="k net">صافي الراتب</td><td class="n net">{_money(s.get('net_pay'))}</td>
</tr>
<tr>
  <td class="k">المبلغ قبل التقريب</td><td class="n">{_money(s.get('amount_before_rounding'))}</td>
  <td class="k">المبلغ بعد التقريب</td><td class="n">{_money(s.get('amount_after_rounding'))}</td>
  <td class="k">العملة</td><td>دينار عراقي (IQD)</td>
</tr>
</tbody></table>

<table class="sign"><tbody><tr>
  <td>المحاسب</td><td>المدقق</td><td>أمين الصرف</td><td>المدير</td>
</tr></tbody></table>
</body></html>"""
	return html


def render_slip_pdf(html):
	"""Convert slip HTML to PDF bytes via wkhtmltopdf (Portrait A4). Requires a bench."""
	from frappe.utils.pdf import get_pdf

	return get_pdf(html, options={"orientation": "Portrait", "page-size": "A4"})
