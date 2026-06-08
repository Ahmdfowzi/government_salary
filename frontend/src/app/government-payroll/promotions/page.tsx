"use client";

// Promotion Requests — read-only list from the Frappe DocType. Grades are
// Government Grade Links (from → to); promotion advances grade + stage.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import type { PromotionRequest } from "@shared/types";

function statusTone(s: string): "success" | "danger" | "neutral" | "warn" {
  if (s === "Approved" || s === "Applied") return "success";
  if (s === "Rejected") return "danger";
  if (s === "Draft") return "neutral";
  return "warn";
}

export default function PromotionsPage() {
  const [list, setList] = useState<PromotionRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.promotions().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    const items = list ?? [];
    const term = q.trim().toLowerCase();
    if (!term) return items;
    return items.filter((r) =>
      [r.name, r.employee_name, r.employee_profile]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(term)),
    );
  }, [list, q]);

  return (
    <div>
      <PageHeader title="الترفيعات" subtitle="طلبات الترفيع (Promotion Request)" />

      <div className="mb-6">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالموظف أو الطلب…" />
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد طلبات ترفيع." />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">الطلب</th>
                  <th className="px-4 py-3 font-medium">الموظف</th>
                  <th className="px-4 py-3 font-medium">الدرجة (من → إلى)</th>
                  <th className="px-4 py-3 font-medium">المرحلة المقترحة</th>
                  <th className="px-4 py-3 font-medium">سنوات الدرجة</th>
                  <th className="px-4 py-3 font-medium">الراتب القديم</th>
                  <th className="px-4 py-3 font-medium">الراتب الجديد</th>
                  <th className="px-4 py-3 font-medium">الحالة</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 num text-slate-700">{r.name}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{r.employee_name ?? r.employee_profile}</td>
                    <td className="px-4 py-3 num text-slate-700">
                      {(r.from_grade_ref ?? "—")} → {(r.to_grade_ref ?? "—")}
                    </td>
                    <td className="px-4 py-3 num text-slate-700">{r.proposed_stage ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-600">{r.years_in_grade ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-600">{r.old_salary?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-800">{r.new_salary?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3"><Pill tone={statusTone(r.approval_status)}>{r.approval_status}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            عدد الطلبات: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
