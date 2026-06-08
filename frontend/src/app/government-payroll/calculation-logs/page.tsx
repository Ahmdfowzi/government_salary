"use client";

// Payroll Calculation Snapshots — immutable, reproducible audit records of every
// engine calculation. Read-only list from the Frappe DocType.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { DataTable, type Column } from "@shared/tables/DataTable";
import { payrollApi } from "@shared/services/api";
import type { PayrollCalculationSnapshot } from "@shared/types";

const TYPE_TONE: Record<string, "info" | "success" | "warn" | "neutral"> = {
  "Active Salary": "info",
  "Annual Increment": "success",
  Promotion: "warn",
};

const columns: Column<PayrollCalculationSnapshot>[] = [
  { key: "snapshot", header: "السجل", numeric: true, render: (s) => s.name },
  { key: "employee", header: "الموظف", render: (s) => s.employee_name ?? s.employee_profile ?? "—" },
  {
    key: "type",
    header: "النوع",
    render: (s) =>
      s.calculation_type ? <Pill tone={TYPE_TONE[s.calculation_type] ?? "neutral"}>{s.calculation_type}</Pill> : "—",
  },
  {
    key: "gradestage",
    header: "الدرجة/المرحلة",
    numeric: true,
    render: (s) => `${s.grade_code ?? "—"}${s.stage != null ? ` / ${s.stage}` : ""}`,
  },
  { key: "gross", header: "الإجمالي", numeric: true, render: (s) => s.gross_amount?.toLocaleString("en-US") ?? "—" },
  { key: "deductions", header: "الاستقطاعات", numeric: true, render: (s) => s.total_deductions?.toLocaleString("en-US") ?? "—" },
  { key: "net", header: "الصافي", numeric: true, render: (s) => s.net_amount?.toLocaleString("en-US") ?? "—" },
  { key: "date", header: "التاريخ", numeric: true, render: (s) => s.period_date ?? s.calc_timestamp ?? "—" },
];

export default function CalculationLogsPage() {
  const [list, setList] = useState<PayrollCalculationSnapshot[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");

  useEffect(() => {
    payrollApi.snapshots().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  const types = useMemo(
    () => Array.from(new Set((list ?? []).map((s) => s.calculation_type).filter(Boolean))) as string[],
    [list],
  );

  const rows = useMemo(() => {
    const items = list ?? [];
    const term = q.trim().toLowerCase();
    return items.filter((s) => {
      const matchesQ =
        !term ||
        [s.name, s.employee_name, s.employee_profile, s.rule_set]
          .filter(Boolean)
          .some((v) => String(v).toLowerCase().includes(term));
      const matchesType = !type || s.calculation_type === type;
      return matchesQ && matchesType;
    });
  }, [list, q, type]);

  return (
    <div>
      <PageHeader
        title="سجلات الاحتساب"
        subtitle="لقطات تدقيق غير قابلة للتعديل وقابلة لإعادة الإنتاج (Payroll Calculation Snapshot)"
      />
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالموظف أو السجل…" />
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
        >
          <option value="">كل الأنواع</option>
          {types.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد لقطات احتساب." />
      ) : (
        <>
          <DataTable columns={columns} rows={rows} rowKey={(s) => s.name} />
          <p className="mt-3 text-xs text-slate-400">
            عدد اللقطات: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
