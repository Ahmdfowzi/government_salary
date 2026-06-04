// Generic, display-only table. Numbers are wrapped with the `.num` class so they
// always render as English numerals (LTR) inside the RTL layout.

export interface Column<T> {
  key: keyof T;
  header: string;
  numeric?: boolean;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  rows,
}: {
  columns: Column<T>[];
  rows: T[];
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-right text-sm">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            {columns.map((c) => (
              <th key={String(c.key)} className="px-4 py-3 font-medium">
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-slate-100">
              {columns.map((c) => (
                <td key={String(c.key)} className="px-4 py-3 text-slate-800">
                  {c.numeric ? (
                    <span className="num">{String(row[c.key] ?? "")}</span>
                  ) : (
                    String(row[c.key] ?? "")
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
