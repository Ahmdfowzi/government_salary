# Copyright (c) 2026, Iraqi Government Payroll
"""Render a Government Payroll Slip to a government-styled RTL Arabic PDF.

FONT (critical, verified with pdffonts): wkhtmltopdf (0.12.6 / Qt-WebKit) ignores
base64 @font-face data URIs AND mis-matches fonts that share a family name, so it
silently embeds DejaVu instead of Cairo. The reliable fix used here:
  1. the bundled Cairo TTFs are renamed to UNIQUE families (CairoReg / CairoMed /
     CairoSemi / CairoBold);
  2. ``_ensure_fonts_installed()`` copies them into the user font dir + fc-cache;
  3. the CSS references those unique families (NO @font-face — it suppresses the
     fontconfig fallback).
After this, pdffonts shows all four Cairo weights embedded and zero DejaVu.

Weights: Title/Net/Ministry = CairoBold, Section headers = CairoSemi, Labels =
CairoMed, Values = CairoReg. (No letter-spacing — it breaks Arabic joining.)
"""

import os
import shutil
import subprocess
from html import escape

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_FONT_FILES = ("Cairo-Regular.ttf", "Cairo-Medium.ttf", "Cairo-SemiBold.ttf", "Cairo-Bold.ttf")
_FONT_INSTALL_DIR = os.path.expanduser("~/.fonts")

NA = "غير متوفر"

_MONTHS_AR = ["", "كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران",
			  "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"]

_fonts_ready = False


def _ensure_fonts_installed():
	"""Copy the bundled Cairo TTFs into the user font dir + refresh fontconfig so
	wkhtmltopdf resolves the `Cairo` families. Idempotent; safe to call per render."""
	global _fonts_ready
	if _fonts_ready:
		return
	try:
		os.makedirs(_FONT_INSTALL_DIR, exist_ok=True)
		for fn in _FONT_FILES:                      # overwrite so font updates propagate
			src = os.path.join(_FONTS_DIR, fn)
			if os.path.exists(src):
				shutil.copyfile(src, os.path.join(_FONT_INSTALL_DIR, fn))
		subprocess.run(["fc-cache", "-f", _FONT_INSTALL_DIR], check=False, timeout=30,
					   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		_fonts_ready = True
	except Exception:
		pass            # rendering still works with a fallback font


def font_debug():
	"""Diagnostic: bundled font paths, install status, and fontconfig matches."""
	info = {"bundled": [], "installed_dir": _FONT_INSTALL_DIR, "installed": [], "fc_list_cairo": []}
	for fn in _FONT_FILES:
		src = os.path.join(_FONTS_DIR, fn)
		info["bundled"].append({"file": src, "exists": os.path.exists(src),
								"size": os.path.getsize(src) if os.path.exists(src) else 0})
		dst = os.path.join(_FONT_INSTALL_DIR, fn)
		if os.path.exists(dst):
			info["installed"].append(dst)
	try:
		out = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=15).stdout
		info["fc_list_cairo"] = [l for l in out.splitlines() if "cairo" in l.lower()]
	except Exception as e:
		info["fc_list_cairo"] = [f"fc-list unavailable: {e}"]
	return info


def _money(v):
	try:
		return f"{int(round(float(v))):,}"
	except (TypeError, ValueError):
		return "0"


def _na(v):
	"""Arabic 'not available' for blank values — never a silent empty cell."""
	return escape(NA if v in (None, "", 0) else str(v))


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
	cls = "v num" if numeric else "v"
	return f'<td class="k">{escape(label)}</td><td class="{cls}">{_na(value)}</td>'


def build_slip_html(slip):
	"""Return a complete one-page, government-styled RTL Arabic slip. Pure."""
	s = slip
	period_label = f"{_month_ar(s.get('payroll_month'))} {_txt(s.get('payroll_year'))}".strip()

	ent_rows = [
		'<tr><td class="r lblm">الراتب الاسمي</td><td></td><td></td>'
		f'<td class="n">{_money(s.get("base_salary"))}</td></tr>'
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

	ded_src = list(s.get("deduction_lines") or []) + [
		{"deduction_name": m.get("description"), "amount": m.get("amount")}
		for m in (s.get("misc_deduction_lines") or [])]
	ded_rows = [
		f'<tr><td class="r">{_txt(d.get("deduction_name"))}</td>'
		f'<td class="n">{_money(d.get("amount"))}</td></tr>' for d in ded_src]
	if not ded_rows:
		ded_rows = ['<tr><td class="r">لا توجد استقطاعات</td><td class="n">0</td></tr>']
	ded_rows += ['<tr><td>&nbsp;</td><td></td></tr>'] * max(0, len(ent_rows) - len(ded_rows))

	logo = s.get("logo_uri")
	logo_html = f'<img class="logo" src="{logo}"/>' if logo else ""

	html = f"""<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>
*{{font-family:"CairoReg",sans-serif;box-sizing:border-box;}}
body{{direction:rtl;color:#0b1324;font-size:11.5px;line-height:1.6;margin:0;padding:16px 20px;}}
.n{{direction:ltr;unicode-bidi:embed;text-align:left;}}
.lblm{{font-family:"CairoMed";}}
.head{{text-align:center;line-height:1.55;}}
.head .logo{{height:62px;margin-bottom:4px;}}
.head .rep{{font-family:"CairoSemi";font-size:12px;color:#334155;}}
.head .min{{font-family:"CairoBold";font-size:18px;}}
.head .dep{{font-family:"CairoMed";font-size:13px;color:#1e293b;}}
.title{{font-family:"CairoBold";font-size:15px;text-align:center;margin:10px 0 12px;
  border:2px solid #0b1324;border-radius:5px;padding:7px;background:#eef2f7;}}
table{{border-collapse:collapse;width:100%;}}
.strip td{{border:1px solid #8aa0b6;padding:5px 8px;}}
.strip .k{{font-family:"CairoMed";background:#eef2f7;white-space:nowrap;}}
.info{{margin-top:9px;}}
.info td{{border:1px solid #8aa0b6;padding:6px 9px;height:26px;}}
.info td.k{{font-family:"CairoMed";background:#eef2f7;white-space:nowrap;width:13%;}}
.info td.v{{font-family:"CairoReg";}}
.cols{{margin-top:12px;}}
.cols>tbody>tr>td.col{{vertical-align:top;width:50%;}}
.cols>tbody>tr>td.gap{{width:10px;}}
h3{{font-family:"CairoSemi";margin:0;font-size:13px;color:#fff;background:#0b1324;
  padding:7px 8px;text-align:center;}}
table.body td,table.body th{{border:1px solid #5b6b7d;padding:6px 9px;}}
table.body thead th{{font-family:"CairoSemi";background:#dfe6ee;font-size:11px;}}
table.body td.r{{text-align:right;}}
table.body td.n,table.body th.n{{text-align:left;direction:ltr;width:24%;}}
table.body tfoot td{{font-family:"CairoSemi";background:#eef2f7;}}
.totals{{margin-top:13px;}}
.totals td{{border:2px solid #0b1324;padding:9px 11px;text-align:center;}}
.totals .k{{font-family:"CairoMed";background:#eef2f7;}}
.totals .net{{font-family:"CairoBold";background:#d8f3df;font-size:15px;}}
.words{{margin-top:7px;border:1px solid #8aa0b6;padding:7px 10px;font-family:"CairoMed";background:#fafbfc;}}
.sign{{margin-top:34px;}}
.sign td{{text-align:center;font-size:11px;color:#334155;padding-top:36px;width:25%;}}
.sign td span{{border-top:1px solid #0b1324;padding-top:6px;font-family:"CairoSemi";color:#0b1324;}}
</style></head><body>

<div class="head">
  {logo_html}
  <div class="rep">جمهورية العراق</div>
  <div class="min">{_na(s.get('entity_name'))}</div>
  <div class="dep">{_na(s.get('department_name'))}</div>
</div>
<div class="title">مفردات راتب لشهر {period_label}</div>

<table class="strip"><tbody><tr>
  <td class="k">التسلسل</td><td class="n">{_na(s.get('list_sequence'))}</td>
  <td class="k">تاريخ الراتب</td><td class="n">{_na(s.get('payroll_date'))}</td>
  <td class="k">أمين الصرف</td><td>{_na(s.get('payment_officer'))}</td>
  <td class="k">رقم أمر الصرف</td><td class="n">{_na(s.get('payment_number'))}</td>
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
	"""Convert slip HTML to PDF via wkhtmltopdf (Portrait A4). The Cairo @font-face
	uses file:// URLs, so local-file access must be enabled for them to load; we
	also install the fonts into fontconfig as a belt-and-suspenders fallback.
	Bench-only."""
	from frappe.utils.pdf import get_pdf

	_ensure_fonts_installed()
	return get_pdf(html, options={"orientation": "Portrait", "page-size": "A4",
								  "margin-top": "8mm", "margin-bottom": "8mm",
								  "enable-local-file-access": ""})
