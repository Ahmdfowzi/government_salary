"use client";

// Government Rule Sets — versioned legal rule packages (active + archived).
// Read-only list from the Frappe DocType.

import { useEffect, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import type { GovernmentRuleSet, RuleStatus } from "@shared/types";

const STATUS_TONE: Record<RuleStatus, "success" | "neutral" | "warn"> = {
  Active: "success",
  Archived: "neutral",
  Draft: "warn",
};
const STATUS_AR: Record<RuleStatus, string> = {
  Active: "فعّالة",
  Archived: "مؤرشفة",
  Draft: "مسودة",
};

export default function RuleSetsPage() {
  const [list, setList] = useState<GovernmentRuleSet[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi.ruleSets().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div>
      <PageHeader title="مجموعات القواعد" subtitle="نسخ حزم القواعد القانونية (Government Rule Set)" />
      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : (list ?? []).length === 0 ? (
        <Empty message="لا توجد مجموعات قواعد." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-right text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">الرمز</th>
                <th className="px-4 py-3 font-medium">الاسم</th>
                <th className="px-4 py-3 font-medium">السنة</th>
                <th className="px-4 py-3 font-medium">من تاريخ</th>
                <th className="px-4 py-3 font-medium">إلى تاريخ</th>
                <th className="px-4 py-3 font-medium">الحالة</th>
              </tr>
            </thead>
            <tbody>
              {(list ?? []).map((r) => (
                <tr key={r.name} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 num font-medium text-slate-900">{r.rule_set_code ?? r.name}</td>
                  <td className="px-4 py-3 text-slate-700">{r.rule_set_name ?? "—"}</td>
                  <td className="px-4 py-3 num text-slate-700">{r.year ?? "—"}</td>
                  <td className="px-4 py-3 num text-slate-600">{r.effective_from ?? "—"}</td>
                  <td className="px-4 py-3 num text-slate-600">{r.effective_to ?? "—"}</td>
                  <td className="px-4 py-3">
                    <Pill tone={STATUS_TONE[r.status] ?? "neutral"}>
                      {STATUS_AR[r.status] ?? r.status}
                    </Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
