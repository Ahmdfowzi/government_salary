"use client";

// Payroll Runs — create form + list. Display/transport only: the create form
// collects inputs and POSTs to the backend (create_payroll_run), which validates
// everything (existence, scope rules, duplicate guard). No workflow or
// authorization logic lives here.

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PageHeader } from "@shared/components/PageHeader";
import { StateBadge } from "@shared/components/StateBadge";
import { FormShell } from "@shared/forms/FormShell";
import { payrollApi } from "@shared/services/api";
import type {
  PayrollRun,
  PayrollPeriod,
  GovernmentRuleSet,
  GovernmentEmployeePayrollProfile,
  GovernmentEntity,
} from "@shared/types";

const SCOPES = ["All", "Government Entity", "Employee"] as const;
const SCOPE_LABELS: Record<string, string> = {
  All: "الكل",
  "Government Entity": "جهة حكومية",
  Employee: "موظف",
};

export default function PayrollRunsPage() {
  const router = useRouter();

  const [runs, setRuns] = useState<PayrollRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Create-form option lists + field state.
  const [periods, setPeriods] = useState<PayrollPeriod[]>([]);
  const [ruleSets, setRuleSets] = useState<GovernmentRuleSet[]>([]);
  const [employees, setEmployees] = useState<GovernmentEmployeePayrollProfile[]>([]);
  const [entities, setEntities] = useState<GovernmentEntity[]>([]);

  const [period, setPeriod] = useState("");
  const [ruleSet, setRuleSet] = useState("");
  const [scope, setScope] = useState<string>("All");
  const [scopeRef, setScopeRef] = useState("");

  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  function loadRuns() {
    payrollApi
      .payrollRuns()
      .then(setRuns)
      .catch((e: Error) => setError(e.message));
  }

  useEffect(() => {
    loadRuns();
    payrollApi.payrollPeriods().then(setPeriods).catch(() => {});
    payrollApi.ruleSets().then(setRuleSets).catch(() => {});
    payrollApi.employees().then(setEmployees).catch(() => {});
    payrollApi.entities().then(setEntities).catch(() => {});
  }, []);

  async function onCreate() {
    setCreating(true);
    setCreateError(null);
    try {
      const res = await payrollApi.createRun(
        period,
        ruleSet,
        scope,
        scope === "All" ? undefined : scopeRef,
      );
      router.push(`/government-payroll/payroll-runs/${encodeURIComponent(res.name)}`);
    } catch (e) {
      setCreateError((e as Error).message);
      setCreating(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="دورات الرواتب"
        subtitle="سير عمل دورات الرواتب — الاعتماد والتقديم والقفل (Payroll Run)"
      />

      {/* Create form */}
      <div className="mb-8">
        <FormShell title="إنشاء دورة رواتب" onSubmit={onCreate}>
          {createError ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {createError}
            </div>
          ) : null}

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">الفترة</span>
            <select
              required
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">— اختر فترة —</option>
              {periods.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">مجموعة القواعد</span>
            <select
              value={ruleSet}
              onChange={(e) => setRuleSet(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2"
            >
              <option value="">— بدون —</option>
              {ruleSets.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">النطاق</span>
            <select
              value={scope}
              onChange={(e) => {
                setScope(e.target.value);
                setScopeRef("");
              }}
              className="rounded-lg border border-slate-300 px-3 py-2"
            >
              {SCOPES.map((s) => (
                <option key={s} value={s}>
                  {SCOPE_LABELS[s]}
                </option>
              ))}
            </select>
          </label>

          {scope !== "All" ? (
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-slate-600">
                {scope === "Employee" ? "الموظف" : "الجهة الحكومية"}
              </span>
              <select
                required
                value={scopeRef}
                onChange={(e) => setScopeRef(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2"
              >
                <option value="">— اختر —</option>
                {(scope === "Employee" ? employees : entities).map((o) => (
                  <option key={o.name} value={o.name}>
                    {o.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <div>
            <button
              type="submit"
              disabled={creating}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {creating ? "…" : "إنشاء الدورة"}
            </button>
          </div>
        </FormShell>
      </div>

      {/* List */}
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
