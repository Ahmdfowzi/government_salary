"use client";

// Allowance Rules — earnings/deductions components and how they are matched and
// valued. Read-only list from the Frappe DocType.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import type { AllowanceRule } from "@shared/types";

export default function AllowancesPage() {
  const [list, setList] = useState<AllowanceRule[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.allowances().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    const items = list ?? [];
    const term = q.trim().toLowerCase();
    if (!term) return items;
    return items.filter((a) =>
      [a.component_code, a.component_name, a.match_value, a.rule_set]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(term)),
    );
  }, [list, q]);

  function value(a: AllowanceRule): string {
    if (a.calculation_type === "Percentage") return a.percentage != null ? `${a.percentage}%` : "—";
    return a.fixed_amount != null ? a.fixed_amount.toLocaleString("en-US") : "—";
  }

  return (
    <div>
      <PageHeader title="المخصصات" subtitle="قواعد المخصصات والاستقطاعات (Allowance Rule)" />

      <div className="mb-6">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالمكوّن أو القيمة…" />
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد قواعد مخصصات." />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">الرمز</th>
                  <th className="px-4 py-3 font-medium">المكوّن</th>
                  <th className="px-4 py-3 font-medium">النوع</th>
                  <th className="px-4 py-3 font-medium">السياق</th>
                  <th className="px-4 py-3 font-medium">المطابقة</th>
                  <th className="px-4 py-3 font-medium">القيمة</th>
                  <th className="px-4 py-3 font-medium">سقف 200%</th>
                  <th className="px-4 py-3 font-medium">الحالة</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.name} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 num font-medium text-slate-900">{a.component_code}</td>
                    <td className="px-4 py-3 text-slate-700">{a.component_name}</td>
                    <td className="px-4 py-3">
                      <Pill tone={a.allowance_type === "Deduction" ? "danger" : "success"}>
                        {a.allowance_type === "Deduction" ? "استقطاع" : "مخصص"}
                      </Pill>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{a.context}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {a.match_key ?? "—"}{a.match_value ? ` · ${a.match_value}` : ""}
                    </td>
                    <td className="px-4 py-3 num text-slate-800">{value(a)}</td>
                    <td className="px-4 py-3 text-slate-600">{a.capped_under_200 ?? "—"}</td>
                    <td className="px-4 py-3">
                      <Pill tone={a.is_active ? "success" : "neutral"}>
                        {a.is_active ? "فعّالة" : "غير فعّالة"}
                      </Pill>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            عدد القواعد: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
