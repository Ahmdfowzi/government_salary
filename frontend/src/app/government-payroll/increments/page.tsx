"use client";

// Annual Increment Requests — read-only list from the Frappe DocType. Grade is
// the Government Grade Link; increments advance only the stage.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import type { AnnualIncrementRequest } from "@shared/types";

function statusTone(s: string): "success" | "danger" | "neutral" | "warn" {
  if (s === "Approved" || s === "Applied") return "success";
  if (s === "Rejected") return "danger";
  if (s === "Draft") return "neutral";
  return "warn";
}

export default function IncrementsPage() {
  const [list, setList] = useState<AnnualIncrementRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.increments().then(setList).catch((e: Error) => setError(e.message));
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
      <PageHeader title="العلاوات السنوية" subtitle="طلبات العلاوة السنوية (Annual Increment Request)" />

      <div className="mb-6">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالموظف أو الطلب…" />
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد طلبات علاوة." />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">الطلب</th>
                  <th className="px-4 py-3 font-medium">الموظف</th>
                  <th className="px-4 py-3 font-medium">الدرجة</th>
                  <th className="px-4 py-3 font-medium">المرحلة</th>
                  <th className="px-4 py-3 font-medium">الراتب الحالي</th>
                  <th className="px-4 py-3 font-medium">الراتب الجديد</th>
                  <th className="px-4 py-3 font-medium">مقدار العلاوة</th>
                  <th className="px-4 py-3 font-medium">تاريخ الاستحقاق</th>
                  <th className="px-4 py-3 font-medium">الحالة</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.name} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 num text-slate-700">{r.name}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{r.employee_name ?? r.employee_profile}</td>
                    <td className="px-4 py-3 num text-slate-700">{r.current_grade_ref ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-700">
                      {r.current_stage ?? "—"}{r.new_stage != null ? ` → ${r.new_stage}` : ""}
                    </td>
                    <td className="px-4 py-3 num text-slate-600">{r.current_salary?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-600">{r.new_salary?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-800">{r.increment_amount?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-600">{r.due_date ?? "—"}</td>
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
