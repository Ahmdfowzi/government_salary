# Copyright (c) 2026, Iraqi Government Payroll
"""Render report data to a PDF (Phase 4 M14).

Two pieces, kept separate so the layout is testable without a bench:

* ``build_html(title, columns, rows, totals)`` — PURE: builds an RTL Arabic HTML
  table from rows the report aggregators already produced. No Frappe, no
  aggregation, no schema — it reuses the column spec passed in (from
  ``report_columns.py``). The bundled open-source **Amiri** font (OFL) is embedded
  as a base64 ``@font-face`` so Arabic shapes correctly regardless of the fonts
  installed in the host/container.
* ``render_pdf(html)`` — thin wrapper over ``frappe.utils.pdf.get_pdf`` (wkhtmltopdf).

Cell formatting matches the Excel exporter for consistency: None -> "",
booleans -> نعم/لا, lists (bank-transfer ``missing`` reasons) -> comma-joined — so
flagged incomplete rows are rendered in full, never dropped.
"""

import base64
import os
from html import escape

_TOTAL_LABEL = "الإجمالي"
_FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "Amiri-Regular.ttf")

_font_uri_cache = None


def _font_data_uri():
	"""base64 data URI for the bundled Amiri font (computed once)."""
	global _font_uri_cache
	if _font_uri_cache is None:
		with open(_FONT_PATH, "rb") as fh:
			b64 = base64.b64encode(fh.read()).decode("ascii")
		_font_uri_cache = "data:font/truetype;base64," + b64
	return _font_uri_cache


def _fmt(value):
	if value is None:
		return ""
	if isinstance(value, bool):
		return "نعم" if value else "لا"
	if isinstance(value, (list, tuple)):
		return "، ".join(str(x) for x in value)
	return str(value)


def _cell(value, tag="td"):
	return "<{t}>{v}</{t}>".format(t=tag, v=escape(_fmt(value)))


def build_html(title, columns, rows, totals=None):
	"""Return a complete RTL Arabic HTML document for the report. Pure."""
	head_cells = "".join(_cell(header, "th") for _key, header in columns)
	body_rows = "".join(
		"<tr>" + "".join(_cell(row.get(key)) for key, _header in columns) + "</tr>"
		for row in rows
	)
	tfoot = ""
	if totals:
		cells = []
		for idx, (key, _header) in enumerate(columns):
			if idx == 0:
				cells.append(_cell(_TOTAL_LABEL))
			elif key in totals:
				cells.append(_cell(totals[key]))
			else:
				cells.append("<td></td>")
		tfoot = "<tfoot><tr>" + "".join(cells) + "</tr></tfoot>"

	return (
		'<!DOCTYPE html><html dir="rtl" lang="ar"><head><meta charset="utf-8"><style>'
		'@font-face{font-family:"AmiriReport";src:url(' + _font_data_uri() + ')'
		' format("truetype");}'
		'*{font-family:"AmiriReport",sans-serif;}'
		'body{direction:rtl;font-size:11px;color:#1f2937;}'
		'h1{font-size:16px;margin:0 0 10px;}'
		'table{width:100%;border-collapse:collapse;}'
		'th,td{border:1px solid #94a3b8;padding:5px 7px;text-align:right;}'
		'thead th{background:#f1f5f9;font-weight:bold;}'
		'tfoot td{font-weight:bold;background:#f8fafc;}'
		'</style></head><body>'
		'<h1>' + escape(title or "") + '</h1>'
		'<table><thead><tr>' + head_cells + '</tr></thead>'
		'<tbody>' + body_rows + '</tbody>' + tfoot + '</table>'
		'</body></html>'
	)


def render_pdf(html):
	"""Convert report HTML to PDF bytes via wkhtmltopdf. Requires a bench."""
	from frappe.utils.pdf import get_pdf

	return get_pdf(html, options={"orientation": "Landscape"})
