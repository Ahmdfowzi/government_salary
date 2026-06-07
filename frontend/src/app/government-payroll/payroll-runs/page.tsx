"use client";

// Payroll Runs — list. Display-only: rows link to the detail route where
// governance actions live. No workflow or authorization logic here.

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { StateBadge } from "@shared/components/StateBadge";
import { payrollApi } from "@shared/services/api";
import type { PayrollRun } from "@shared/types";

export default function PayrollRunsPage() {
  const [runs, setRuns] = useState<PayrollRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi
      .payrollRuns()
      .then(setRuns)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div>
      <PageHeader
        title="دورات الرواتب"
        subtitle="سير عمل دورات الرواتب — الاعتماد والتقديم والقفل (Payroll Run)"
      />

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {runs === null && !error ? (
        <p className="text-sm text-slate-500">جارٍ التحميل…</p>
      ) : null}

      {runs && runs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
          لا توجد دورات رواتب.
        </div>
      ) : null}

      {runs && runs.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-right text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">الدورة</th>
                <th className="px-4 py-3 font-medium">الفترة</th>
                <th className="px-4 py-3 font-medium">الحالة</th>
                <th className="px-4 py-3 font-medium">حالة التنفيذ</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.name} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/government-payroll/payroll-runs/${encodeURIComponent(run.name)}`}
                      className="font-medium text-sky-700 hover:underline"
                    >
                      <span className="num">{run.name}</span>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-800">
                    <span className="num">{run.payroll_period ?? ""}</span>
                  </td>
                  <td className="px-4 py-3">
                    <StateBadge state={run.workflow_state ?? "Draft"} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{run.run_status ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
