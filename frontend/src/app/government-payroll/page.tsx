"use client";

// Dashboard — payroll status summary, latest runs (locked/unlocked + run status),
// and role-grouped quick actions. Read-only overview from existing APIs.

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { StateBadge } from "@shared/components/StateBadge";
import { StatCard } from "@shared/components/Card";
import { Pill } from "@shared/components/Pill";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canExportJournal, canManagePayroll } from "@shared/services/roles";
import type { PayrollRun } from "@shared/types";

const IN_PROGRESS = ["Draft", "Calculated", "Under Review", "Approved"];

function QuickLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-sky-700 hover:border-sky-300 hover:bg-sky-50"
    >
      {label}
    </Link>
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
    runs?.filter((r) => IN_PROGRESS.includes(r.workflow_state ?? "Draft")).length ?? 0;
  const submitted =
    runs?.filter((r) => ["Submitted", "Locked"].includes(r.workflow_state ?? "")).length ?? 0;
  const latest = (runs ?? []).slice(-6).reverse();

  const general = [
    { href: "/government-payroll/reports", label: "التقارير والتصدير" },
    { href: "/government-payroll/pension", label: "كشف التقاعد" },
    { href: "/government-payroll/employees", label: "الموظفون" },
  ];
  const management = [
    canManagePayroll(roles) && { href: "/government-payroll/payroll-runs", label: "إدارة دورات الرواتب" },
    canExportJournal(roles) && { href: "/government-payroll/accounting-journal", label: "القيد المحاسبي" },
  ].filter(Boolean) as { href: string; label: string }[];

  return (
    <div>
      <PageHeader title="لوحة التحكم" subtitle="نظرة عامة على رواتب موظفي الدولة العراقية" />

      {error ? <div className="mb-6"><ErrorBanner message={error} /></div> : null}

      {/* Summary cards */}
      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="إجمالي الدورات" value={total} />
        <StatCard label="قيد الإعداد" value={inProgress} accent="text-amber-600" />
        <StatCard label="مُقدّمة / مقفلة" value={submitted} accent="text-emerald-600" />
        <StatCard label="مقفلة" value={locked} accent="text-slate-800" hint="سجلات نهائية غير قابلة للتعديل" />
      </div>

      {/* Quick actions, grouped */}
      <h2 className="mb-3 text-sm font-semibold text-slate-900">إجراءات سريعة</h2>
      <div className="mb-2 text-xs text-slate-400">عام</div>
      <div className="mb-4 flex flex-wrap gap-3">
        {general.map((a) => <QuickLink key={a.href} {...a} />)}
      </div>
      {management.length ? (
        <>
          <div className="mb-2 text-xs text-slate-400">إدارة (حسب الصلاحية)</div>
          <div className="mb-8 flex flex-wrap gap-3">
            {management.map((a) => <QuickLink key={a.href} {...a} />)}
          </div>
        </>
      ) : (
        <div className="mb-8" />
      )}

      {/* Latest runs */}
      <h2 className="mb-3 text-sm font-semibold text-slate-900">أحدث دورات الرواتب</h2>
      {runs === null && !error ? (
        <Loading />
      ) : latest.length === 0 ? (
        <Empty message="لا توجد دورات رواتب بعد." />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-right text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">الدورة</th>
                <th className="px-4 py-3 font-medium">الفترة</th>
                <th className="px-4 py-3 font-medium">الحالة</th>
                <th className="px-4 py-3 font-medium">التنفيذ</th>
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
                  <td className="px-4 py-3"><StateBadge state={run.workflow_state ?? "Draft"} /></td>
                  <td className="px-4 py-3 text-xs text-slate-500">{run.run_status ?? "—"}</td>
                  <td className="px-4 py-3">
                    {run.workflow_state === "Locked" ? (
                      <Pill tone="dark">🔒 مقفلة</Pill>
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
