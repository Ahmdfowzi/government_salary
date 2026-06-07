// Client-side CSV export from already-fetched JSON rows. No backend, no deps.
// Read-only: serializes data the report endpoints already returned.

type Row = Record<string, unknown>;

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const s = String(value);
  // Quote if the value contains a comma, quote or newline (RFC 4180).
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** Build CSV text from rows using `columns` (key + header) for order/labels. */
export function toCsv(rows: Row[], columns: { key: string; header: string }[]): string {
  const head = columns.map((c) => cell(c.header)).join(",");
  const body = rows.map((r) => columns.map((c) => cell(r[c.key])).join(","));
  // Prepend a UTF-8 BOM so Excel opens Arabic headers correctly.
  return "﻿" + [head, ...body].join("\r\n");
}

/** Trigger a browser download of `rows` as `<filename>.csv`. */
export function downloadCsv(
  filename: string,
  rows: Row[],
  columns: { key: string; header: string }[],
): void {
  const blob = new Blob([toCsv(rows, columns)], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
