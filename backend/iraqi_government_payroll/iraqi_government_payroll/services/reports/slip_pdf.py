# Copyright (c) 2026, Iraqi Government Payroll
"""Render a Government Payroll Slip to a printable, government-styled RTL Arabic
PDF (مفردات راتب).

* ``build_slip_html(slip)`` — PURE: builds the layout (RTL, bundled **Cairo**
  regular + bold embedded as base64 @font-face, bold Arabic labels, English
  numerals). No Frappe — testable without a bench.
* ``render_slip_pdf(html)`` — wkhtmltopdf (Portrait A4). The layout uses tables
  only (old WebKit has no flexbox).
"""

import base64
import os
from html import escape

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_CAIRO = os.path.join(_FONTS_DIR, "Cairo-Regular.ttf")
_CAIRO_BOLD = os.path.join(_FONTS_DIR, "Cairo-Bold.ttf")
_AMIRI = os.path.join(_FONTS_DIR, "Amiri-Regular.ttf")

_font_cache = None

_MONTHS_AR = ["", "كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران",
			  "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"]


def _uri(path):
	with open(path, "rb") as fh:
		return "data:font/truetype;base64," + base64.b64encode(fh.read()).decode("ascii")


def _fonts():
	"""(regular_uri, bold_uri) for the slip — Cairo, with Amiri as a fallback."""
	global _font_cache
	if _font_cache is None:
		reg = _CAIRO if os.path.exists(_CAIRO) else _AMIRI
		bold = _CAIRO_BOLD if os.path.exists(_CAIRO_BOLD) else reg
		_font_cache = (_uri(reg), _uri(bold))
	return _font_cache


def _money(v):
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
	return f"{f:g}%" if f else ""


def _month_ar(m):
	try:
		return _MONTHS_AR[int(m)]
	except (TypeError, ValueError, IndexError):
		return ""


def _kv(label, value, numeric=False):
	cls = ' class="num"' if numeric else ""
	return (f'<td class="k">{escape(label)}</td>'
			f'<td{cls}>{_txt(value)}</td>')


def build_slip_html(slip):
	"""Return a complete one-page, government-styled RTL Arabic slip. Pure."""
	reg, bold = _fonts()
	s = slip
	month = _month_ar(s.get("payroll_month"))
	period_label = f"{month} {_txt(s.get('payroll_year'))}".strip()

	# ---- entitlement rows: basic salary first, then Arabic-named allowances ----
	ent_rows = [
		'<tr><td class="r b">الراتب الاسمي</td><td></td><td></td>'
		f'<td class="n b">{_money(s.get("base_salary"))}</td></tr>'
	]
	for a in s.get("allowance_lines") or []:
		ent_rows.append(
			"<tr>"
			f'<td class="r">{_txt(a.get("allowance_name"))}</td>'
			f'<td class="n">{_pct(a.get("percentage"))}</td>'
			f'<td class="n">{_money(a.get("base_amount")) if a.get("base_amount") else ""}</td>'
			f'<td class="n">{_money(a.get("amount"))}</td>'
			"</tr>"
		)
	if s.get("adjustment_amount"):
		ent_rows.append('<tr><td class="r">فرق الراتب المحمي</td><td></td><td></td>'
						f'<td class="n">{_money(s.get("adjustment_amount"))}</td></tr>')
	if s.get("total_rewards"):
		ent_rows.append('<tr><td class="r">المكافآت</td><td></td><td></td>'
						f'<td class="n">{_money(s.get("total_rewards"))}</td></tr>')
	# pad so both columns are the same visual height
	ded_src = list(s.get("deduction_lines") or []) + [
		{"deduction_name": m.get("description"), "amount": m.get("amount")}
		for m in (s.get("misc_deduction_lines") or [])]
	ded_rows = [
		f'<tr><td class="r">{_txt(d.get("deduction_name"))}</td>'
		f'<td class="n">{_money(d.get("amount"))}</td></tr>' for d in ded_src]
	if not ded_rows:
		ded_rows = ['<tr><td class="r">لا توجد استقطاعات</td><td class="n">0</td></tr>']
	pad = len(ent_rows) - len(ded_rows)
	ded_rows += ['<tr><td>&nbsp;</td><td></td></tr>'] * max(0, pad)

	html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
@font-face{{font-family:"Slip";src:url({reg}) format("truetype");font-weight:normal;}}
@font-face{{font-family:"SlipB";src:url({bold}) format("truetype");font-weight:normal;}}
*{{font-family:"Slip",sans-serif;box-sizing:border-box;}}
body{{direction:rtl;color:#0b1324;font-size:11.5px;margin:0;padding:16px 18px;}}
.b{{font-family:"SlipB";}}
.n{{direction:ltr;unicode-bidi:embed;text-align:left;}}
.gov{{text-align:center;line-height:1.5;}}
.gov .rep{{font-size:11px;color:#475569;}}
.gov .min{{font-family:"SlipB";font-size:17px;}}
.gov .dep{{font-size:12.5px;color:#1e293b;}}
.title{{font-family:"SlipB";font-size:15px;text-align:center;margin:8px 0 10px;
  border:2px solid #0b1324;border-radius:4px;padding:6px;background:#eef2f7;}}
table{{border-collapse:collapse;width:100%;}}
.strip td{{border:1px solid #94a3b8;padding:4px 7px;}}
.strip .k{{font-family:"SlipB";background:#f1f5f9;white-space:nowrap;}}
.info{{margin-top:8px;}}
.info td{{border:1px solid #94a3b8;padding:5px 8px;height:24px;}}
.info td.k{{font-family:"SlipB";background:#f1f5f9;white-space:nowrap;width:13%;color:#0b1324;}}
.cols{{margin-top:10px;}}
.cols>tbody>tr>td.col{{vertical-align:top;width:50%;}}
.cols>tbody>tr>td.gap{{width:8px;}}
h3{{font-family:"SlipB";margin:0;font-size:13px;color:#fff;background:#0b1324;
  padding:6px 8px;text-align:center;letter-spacing:.5px;}}
table.body td,table.body th{{border:1px solid #64748b;padding:5px 8px;}}
table.body thead th{{font-family:"SlipB";background:#e2e8f0;font-size:11px;}}
table.body td.r{{text-align:right;}}
table.body td.n,table.body th.n{{text-align:left;direction:ltr;width:24%;}}
table.body tfoot td{{font-family:"SlipB";background:#f1f5f9;}}
.totals{{margin-top:12px;}}
.totals td{{border:2px solid #0b1324;padding:8px 10px;text-align:center;}}
.totals .k{{font-family:"SlipB";background:#f1f5f9;}}
.totals .net{{font-family:"SlipB";background:#dcfce7;font-size:15px;}}
.words{{margin-top:6px;border:1px solid #94a3b8;padding:6px 9px;font-family:"SlipB";background:#fafafa;}}
.sign{{margin-top:30px;}}
.sign td{{text-align:center;font-size:11px;color:#334155;padding-top:34px;width:25%;}}
.sign td span{{border-top:1px solid #0b1324;padding-top:5px;font-family:"SlipB";color:#0b1324;}}
</style></head><body>

<div class="gov">
  <div class="rep">جمهورية العراق</div>
  <div class="min">{_txt(s.get('entity_name')) or '—'}</div>
  <div class="dep">{_txt(s.get('department_name'))}</div>
</div>
<div class="title">مفردات راتب لشهر {period_label}</div>

<table class="strip"><tbody><tr>
  <td class="k">التسلسل</td><td class="n">{_txt(s.get('list_sequence'))}</td>
  <td class="k">تاريخ الراتب</td><td class="n">{_txt(s.get('payroll_date'))}</td>
  <td class="k">أمين الصرف</td><td>{_txt(s.get('payment_officer'))}</td>
  <td class="k">رقم أمر الصرف</td><td class="n">{_txt(s.get('payment_number'))}</td>
</tr></tbody></table>

<table class="info"><tbody>
<tr>{_kv('الاسم', s.get('employee_name'))}{_kv('الرقم الوظيفي', s.get('employee_number'), True)}{_kv('الرقم الوطني الموحد', s.get('unified_national_id'), True)}</tr>
<tr>{_kv('العنوان الوظيفي', s.get('position_title'))}{_kv('الشهادة', s.get('qualification'))}{_kv('الحالة الاجتماعية', s.get('marital_status'))}</tr>
<tr>{_kv('الدرجة', s.get('grade'), True)}{_kv('المرحلة', s.get('stage'), True)}{_kv('سنة الترقية', s.get('promotion_year'), True)}</tr>
<tr>{_kv('تاريخ التعيين', s.get('appointment_date'), True)}{_kv('سنوات الخدمة', s.get('years_of_service'), True)}{_kv('رصيد الإجازة الاعتيادية', s.get('leave_balance_annual'), True)}</tr>
</tbody></table>

<table class="cols"><tbody><tr>
  <td class="col">
    <h3>الاستحقاقات</h3>
    <table class="body">
      <thead><tr><th class="r">البيان</th><th class="n">النسبة</th><th class="n">الأساس</th><th class="n">المبلغ</th></tr></thead>
      <tbody>{''.join(ent_rows)}</tbody>
      <tfoot><tr><td class="r" colspan="3">مجموع الاستحقاقات</td><td class="n">{_money(s.get('total_entitlement'))}</td></tr></tfoot>
    </table>
  </td>
  <td class="gap"></td>
  <td class="col">
    <h3>الاستقطاعات</h3>
    <table class="body">
      <thead><tr><th class="r">البيان</th><th class="n">المبلغ</th></tr></thead>
      <tbody>{''.join(ded_rows)}</tbody>
      <tfoot><tr><td class="r">مجموع الاستقطاعات</td><td class="n">{_money(s.get('total_deductions'))}</td></tr></tfoot>
    </table>
  </td>
</tr></tbody></table>

<table class="totals"><tbody>
<tr>
  <td class="k">مجموع الاستحقاقات</td><td class="n">{_money(s.get('total_entitlement'))}</td>
  <td class="k">مجموع الاستقطاعات</td><td class="n">{_money(s.get('total_deductions'))}</td>
  <td class="net">صافي الراتب</td><td class="net n">{_money(s.get('net_pay'))}</td>
</tr>
<tr>
  <td class="k">المبلغ قبل التقريب</td><td class="n">{_money(s.get('amount_before_rounding'))}</td>
  <td class="k">المبلغ بعد التقريب</td><td class="n">{_money(s.get('amount_after_rounding'))}</td>
  <td class="k">العملة</td><td>دينار عراقي</td>
</tr>
</tbody></table>

<div class="words">المبلغ كتابةً: فقط <span class="num">{_money(s.get('amount_after_rounding'))}</span> دينار عراقي لا غير.</div>

<table class="sign"><tbody><tr>
  <td><span>مُعدّ القائمة</span></td><td><span>المدقّق</span></td><td><span>المحاسب</span></td><td><span>أمين الصرف</span></td>
</tr></tbody></table>
</body></html>"""
	return html


def render_slip_pdf(html):
	"""Convert slip HTML to PDF bytes via wkhtmltopdf (Portrait A4). Requires a bench."""
	from frappe.utils.pdf import get_pdf

	return get_pdf(html, options={"orientation": "Portrait", "page-size": "A4",
								  "margin-top": "8mm", "margin-bottom": "8mm"})
