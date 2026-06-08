"use client";

// Payroll Calculation Snapshots — immutable, reproducible audit records of every
// engine calculation. Read-only list from the Frappe DocType.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import type { PayrollCalculationSnapshot } from "@shared/types";

const TYPE_TONE: Record<string, "info" | "success" | "warn" | "neutral"> = {
  "Active Salary": "info",
  "Annual Increment": "success",
  Promotion: "warn",
};

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
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">السجل</th>
                  <th className="px-4 py-3 font-medium">الموظف</th>
                  <th className="px-4 py-3 font-medium">النوع</th>
                  <th className="px-4 py-3 font-medium">الدرجة/المرحلة</th>
                  <th className="px-4 py-3 font-medium">الإجمالي</th>
                  <th className="px-4 py-3 font-medium">الاستقطاعات</th>
                  <th className="px-4 py-3 font-medium">الصافي</th>
                  <th className="px-4 py-3 font-medium">التاريخ</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.name} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 num text-slate-700">{s.name}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{s.employee_name ?? s.employee_profile ?? "—"}</td>
                    <td className="px-4 py-3">
                      {s.calculation_type ? (
                        <Pill tone={TYPE_TONE[s.calculation_type] ?? "neutral"}>{s.calculation_type}</Pill>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 num text-slate-600">
                      {(s.grade_code ?? "—")}{s.stage != null ? ` / ${s.stage}` : ""}
                    </td>
                    <td className="px-4 py-3 num text-slate-700">{s.gross_amount?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-600">{s.total_deductions?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num font-medium text-slate-900">{s.net_amount?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-500">{s.period_date ?? s.calc_timestamp ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            عدد اللقطات: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
