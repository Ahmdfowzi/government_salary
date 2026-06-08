"use client";

// Salary Scale — every grade/stage and its basic salary, read from the
// Government Salary Scale `details` child table (the legal source of basic pay).

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { loadScales } from "@shared/services/salary";
import type { GovernmentSalaryScale, GovernmentSalaryScaleDetail } from "@shared/types";

interface Row extends GovernmentSalaryScaleDetail {
  scale: string;
  rule_set: string;
}

export default function SalaryScalePage() {
  const [scales, setScales] = useState<GovernmentSalaryScale[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    loadScales()
      .then((s) => setScales(s.scales))
      .catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo<Row[]>(() => {
    const all: Row[] = [];
    for (const s of scales ?? []) {
      for (const d of s.details ?? []) {
        all.push({ ...d, scale: s.scale_name ?? s.name, rule_set: s.rule_set });
      }
    }
    all.sort((a, b) => {
      const ga = Number(a.grade_code), gb = Number(b.grade_code);
      const an = Number.isNaN(ga), bn = Number.isNaN(gb);
      if (an !== bn) return an ? 1 : -1; // senior (non-numeric) grades last
      if (!an && ga !== gb) return ga - gb;
      if (an && a.grade_code !== b.grade_code) return String(a.grade_code).localeCompare(String(b.grade_code));
      return a.stage - b.stage;
    });
    const term = q.trim().toLowerCase();
    if (!term) return all;
    return all.filter((r) => String(r.grade_code ?? r.grade).toLowerCase().includes(term));
  }, [scales, q]);

  return (
    <div>
      <PageHeader title="سلم الرواتب" subtitle="جدول الدرجات والمراحل والرواتب الأساسية (Government Salary Scale)" />

      <div className="mb-6">
        <SearchInput value={q} onChange={setQ} placeholder="تصفية حسب الدرجة…" />
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {scales === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد بيانات سلم رواتب." />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">الدرجة</th>
                  <th className="px-4 py-3 font-medium">النوع</th>
                  <th className="px-4 py-3 font-medium">المرحلة</th>
                  <th className="px-4 py-3 font-medium">الراتب الأساسي</th>
                  <th className="px-4 py-3 font-medium">العلاوة السنوية</th>
                  <th className="px-4 py-3 font-medium">سنوات الترفيع</th>
                  <th className="px-4 py-3 font-medium">مجموعة القواعد</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={`${r.rule_set}-${r.grade_code ?? r.grade}-${r.stage}-${i}`} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 num font-medium text-slate-900">{r.grade_code ?? r.grade}</td>
                    <td className="px-4 py-3">
                      <Pill tone={r.grade_type === "Senior" ? "info" : "neutral"}>
                        {r.grade_type === "Senior" ? "عليا" : "اعتيادية"}
                      </Pill>
                    </td>
                    <td className="px-4 py-3 num text-slate-700">{r.stage}</td>
                    <td className="px-4 py-3 num font-medium text-slate-900">{r.basic_salary?.toLocaleString("en-US")}</td>
                    <td className="px-4 py-3 num text-slate-600">{r.annual_increment?.toLocaleString("en-US") ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-600">{r.promotion_years ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-500">{r.rule_set}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            عدد المدخلات: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
