// Generic, display-only table driven by a SINGLE `columns` array so the header
// (<th>) and every cell (<td>) are rendered from the same definition, in the same
// order. This guarantees each value sits under its own header — in LTR or RTL —
// without ever manually reversing cells.
//
// - Table direction stays RTL (text-right); column order is source order.
// - Arabic/text cells are right-aligned; numeric cells use tabular-nums and wrap
//   their CONTENT in the `.num` helper (English numerals, LTR). IMPORTANT: `.num`
//   sets `display:inline-block`, so it must live on an inner <span>, never on the
//   <td>/<th> itself — putting it on a cell drops it out of the table grid and
//   shifts columns (the RTL "misalignment" bug this component fixes).

import type { ReactNode } from "react";

export interface Column<T> {
  /** Stable identity for the column (React key); not used for data access. */
  key: string;
  /** Arabic header label. */
  header: string;
  /** Cell content for a row. */
  render: (row: T) => ReactNode;
  /** Right-align + tabular English numerals for numbers. */
  numeric?: boolean;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T, index: number) => string;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-right text-sm">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className={`px-4 py-3 font-medium ${c.numeric ? "tabular-nums" : ""}`}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={rowKey(row, i)} className="border-t border-slate-100 hover:bg-slate-50">
              {columns.map((c) => (
                <td key={c.key} className={`px-4 py-3 ${c.numeric ? "text-slate-800" : "text-slate-700"}`}>
                  {/* `.num` stays on an inner span so the <td> remains a table-cell. */}
                  {c.numeric ? <span className="num tabular-nums">{c.render(row)}</span> : c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
