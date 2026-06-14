"use client";

// Payroll Run — governance detail + actions.
//
// All workflow/authorization logic stays on the backend:
//   * action buttons are rendered ONLY from `allowed_actions` (M6),
//   * after every successful action we RE-FETCH get_run_governance — workflow
//     state is never derived or cached locally,
//   * errors (wrong state / unauthorized / blocking errors) come from the backend.
// This component only renders what the API returns.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { PageHeader } from "@shared/components/PageHeader";
import { StateBadge } from "@shared/components/StateBadge";
import { payrollApi } from "@shared/services/api";
import type { RunGovernance } from "@shared/types";

// Presentation-only labels (i18n). These do NOT decide which buttons appear —
// that is `allowed_actions` from the backend.
const ACTION_LABELS: Record<string, string> = {
  calculate: "احتساب",
  submit_for_review: "إرسال للمراجعة",
  approve: "اعتماد",
  submit: "تقديم",
  cancel: "إلغاء",
  lock: "قفل",
  unlock: "فتح القفل",
};

// Per-stage audit fields (read-only), in workflow order.
const AUDIT_ROWS: { by: string; on: string; label: string }[] = [
  { by: "calculated_by", on: "calculated_on", label: "الاحتساب" },
  { by: "reviewed_by", on: "reviewed_on", label: "إرسال للمراجعة" },
  { by: "approved_by", on: "approved_on", label: "الاعتماد" },
  { by: "submitted_by", on: "submitted_on", label: "التقديم" },
  { by: "locked_by", on: "locked_on", label: "القفل" },
  { by: "unlocked_by", on: "unlocked_on", label: "فتح القفل" },
];

export default function PayrollRunDetailPage() {
  const params = useParams<{ name: string }>();
  const name = decodeURIComponent(params.name);

  const [gov, setGov] = useState<RunGovernance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);

  const load = useCallback(() => {
    return payrollApi
      .runGovernance(name)
      .then((g) => {
        setGov(g);
        setError(null);
      })
      .catch((e: Error) => setError(e.message));
  }, [name]);

  useEffect(() => {
    load();
  }, [load]);

  async function act(action: string) {
    setBusy(action);
    setError(null);
    try {
      if (action === "calculate") {
        // Large runs are calculated by a background worker so they never hit the
        // HTTP timeout; enqueue then poll until the run leaves Queued/Processing.
        await runCalculationAsync();
      } else {
        await payrollApi.runAction(name, action);
      }
      await load(); // dynamic re-fetch — never derive workflow state locally
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
      setProgress(null);
    }
  }

  // Enqueue the calculation and poll its status. The backend is authoritative; we
  // only display progress and surface a Failed run. Capped so the UI never hangs
  // (if the worker is slow the run keeps processing in the background).
  async function runCalculationAsync() {
    await payrollApi.enqueueCalculation(name);
    setProgress("تم إرسال الاحتساب إلى المعالجة في الخلفية…");
    const MAX_POLLS = 400; // ~10 min at 1.5s; then defer to a manual refresh
    for (let i = 0; i < MAX_POLLS; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const s = await payrollApi.calculationStatus(name);
      if (s.done) {
        if (s.failed) {
          throw new Error("فشل احتساب الرواتب. راجع سجل الأخطاء في الدورة.");
        }
        return;
      }
      if (
        typeof s.processed_count === "number" &&
        typeof s.total_employees === "number" &&
        s.total_employees > 0
      ) {
        setProgress(`جارٍ الاحتساب… (${s.processed_count}/${s.total_employees})`);
      } else {
        setProgress("جارٍ الاحتساب في الخلفية…");
      }
    }
    setProgress(
      "ما زال الاحتساب قيد المعالجة في الخلفية. يمكنك تحديث الصفحة لاحقاً لمتابعة الحالة.",
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/government-payroll/payroll-runs"
          className="text-sm text-sky-700 hover:underline"
        >
          → العودة إلى دورات الرواتب
        </Link>
      </div>

      <PageHeader title="دورة رواتب" subtitle={name} />

      {error ? (
        <div className="mb-6 rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {gov === null && !error ? (
        <p className="text-sm text-slate-500">جارٍ التحميل…</p>
      ) : null}

      {gov ? (
        <div className="flex flex-col gap-6">
          {/* State + summary */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-center gap-4">
              <StateBadge state={gov.workflow_state} />
              <span className="text-sm text-slate-500">
                حالة التنفيذ: <span className="text-slate-800">{gov.run_status ?? "—"}</span>
              </span>
              <span className="text-sm text-slate-500">
                الأخطاء:{" "}
                <span className="num text-slate-800">{gov.error_count ?? 0}</span>
              </span>
            </div>
          </section>

          {/* Locked / snapshot explanation */}
          {gov.workflow_state === "Locked" ? (
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-4 text-sm text-slate-700">
              🔒 هذه الدورة <strong>مقفلة</strong> وتُعدّ سجلاً نهائياً غير قابل
              للتعديل. تُقرأ التقارير والقيود من <strong>اللقطة الثابتة</strong>
              (Snapshot) لضمان عدم تغيّر الأرقام التاريخية. لا يمكن إعادة الاحتساب أو
              الحذف؛ ويتطلب فتح القفل صلاحية إدارية.
            </div>
          ) : null}

          {/* Actions — strictly from allowed_actions */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-900">الإجراءات المتاحة</h2>
            {progress ? (
              <div className="mb-3 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-800">
                {progress}
              </div>
            ) : null}
            {gov.allowed_actions.length === 0 ? (
              <p className="text-sm text-slate-400">لا توجد إجراءات متاحة في هذه الحالة.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {gov.allowed_actions.map((action) => (
                  <button
                    key={action}
                    type="button"
                    onClick={() => act(action)}
                    disabled={busy !== null}
                    className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {busy === action ? "…" : ACTION_LABELS[action] ?? action}
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Audit trail (read-only) */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-900">سجل المسؤوليات</h2>
            {AUDIT_ROWS.filter((r) => gov.audit[r.by]).length === 0 ? (
              <p className="text-sm text-slate-400">لا يوجد سجل بعد.</p>
            ) : (
              <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {AUDIT_ROWS.filter((r) => gov.audit[r.by]).map((r) => (
                  <div key={r.by} className="flex flex-col rounded-lg bg-slate-50 px-3 py-2">
                    <dt className="text-xs text-slate-500">{r.label}</dt>
                    <dd className="text-sm text-slate-800">
                      {gov.audit[r.by]}
                      {gov.audit[r.on] ? (
                        <span className="num mr-2 text-xs text-slate-400">{gov.audit[r.on]}</span>
                      ) : null}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          {/* Event timeline (read-only, oldest first) */}
          <section className="rounded-xl border border-slate-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-900">سجل الأحداث</h2>
            {gov.events.length === 0 ? (
              <p className="text-sm text-slate-400">لا توجد أحداث.</p>
            ) : (
              <ol className="flex flex-col gap-3">
                {gov.events.map((ev, i) => (
                  <li
                    key={i}
                    className="flex flex-wrap items-center gap-3 border-r-2 border-sky-200 pr-3"
                  >
                    <span className="text-sm font-medium text-slate-900">
                      {ACTION_LABELS[ev.action] ?? ev.action}
                    </span>
                    <span
                      dir="ltr"
                      className="inline-flex items-center gap-1 text-xs text-slate-500"
                    >
                      <StateBadge state={ev.from_state} />
                      <span>→</span>
                      <StateBadge state={ev.to_state} />
                    </span>
                    <span className="text-xs text-slate-600">{ev.actor}</span>
                    <span className="num text-xs text-slate-400">{ev.event_timestamp}</span>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
