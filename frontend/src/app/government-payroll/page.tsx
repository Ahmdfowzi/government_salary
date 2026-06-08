"use client";

// Dashboard — payroll status summary, latest runs (locked/unlocked indicators),
// and role-aware quick actions. Read-only overview; all data from existing APIs.

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { StateBadge } from "@shared/components/StateBadge";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canExportJournal } from "@shared/services/roles";
import type { PayrollRun } from "@shared/types";

function StatCard({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold num ${accent ?? "text-slate-900"}`}>{value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { roles } = useRoles();
  const [runs, setRuns] = useState<PayrollRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi.payrollRuns().then(setRuns).catch((e: Error) => setError(e.message));
  }, []);

  const total = runs?.length ?? 0;
  const locked = runs?.filter((r) => r.workflow_state === "Locked").length ?? 0;
  const inProgress =
    runs?.filter((r) =>
      ["Draft", "Calculated", "Under Review", "Approved"].includes(r.workflow_state ?? "Draft"),
    ).length ?? 0;
  const submitted =
    runs?.filter((r) => ["Submitted", "Locked"].includes(r.workflow_state ?? "")).length ?? 0;

  const latest = (runs ?? []).slice(-6).reverse();

  const quickActions = [
    { href: "/government-payroll/payroll-runs", label: "دورات الرواتب", show: true },
    { href: "/government-payroll/reports", label: "التقارير والتصدير", show: true },
    { href: "/government-payroll/pension", label: "كشف التقاعد", show: true },
    {
      href: "/government-payroll/accounting-journal",
      label: "القيد المحاسبي",
      show: canExportJournal(roles),
    },
  ].filter((a) => a.show);

  return (
    <div>
      <PageHeader
        title="لوحة التحكم"
        subtitle="نظرة عامة على رواتب موظفي الدولة العراقية"
      />

      {error ? (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {/* Summary cards */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="إجمالي الدورات" value={total} />
        <StatCard label="قيد الإعداد" value={inProgress} accent="text-amber-600" />
        <StatCard label="مُقدّمة / مقفلة" value={submitted} accent="text-emerald-600" />
        <StatCard label="مقفلة" value={locked} accent="text-slate-800" />
      </div>

      {/* Quick actions */}
      <h2 className="mb-3 text-sm font-semibold text-slate-900">إجراءات سريعة</h2>
      <div className="mb-8 flex flex-wrap gap-3">
        {quickActions.map((a) => (
          <Link
            key={a.href}
            href={a.href}
            className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-sky-700 hover:border-sky-300 hover:bg-sky-50"
          >
            {a.label}
          </Link>
        ))}
      </div>

      {/* Latest runs */}
      <h2 className="mb-3 text-sm font-semibold text-slate-900">أحدث دورات الرواتب</h2>
      {runs === null && !error ? (
        <p className="text-sm text-slate-500">جارٍ التحميل…</p>
      ) : latest.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          لا توجد دورات رواتب بعد.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-right text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">الدورة</th>
                <th className="px-4 py-3 font-medium">الفترة</th>
                <th className="px-4 py-3 font-medium">الحالة</th>
                <th className="px-4 py-3 font-medium">الإقفال</th>
              </tr>
            </thead>
            <tbody>
              {latest.map((run) => (
                <tr key={run.name} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/government-payroll/payroll-runs/${encodeURIComponent(run.name)}`}
                      className="font-medium text-sky-700 hover:underline num"
                    >
                      {run.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-800 num">{run.payroll_period ?? ""}</td>
                  <td className="px-4 py-3">
                    <StateBadge state={run.workflow_state ?? "Draft"} />
                  </td>
                  <td className="px-4 py-3">
                    {run.workflow_state === "Locked" ? (
                      <span className="text-xs font-medium text-slate-700">🔒 مقفلة</span>
                    ) : (
                      <span className="text-xs text-slate-400">مفتوحة</span>
                    )}
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
