"use client";

// Accounting journal (Phase 4 M15) — read-only PROPOSAL. The backend builds
// balanced debit/credit rows from a run's already-computed figures + the Payroll
// Account Mapping (entered in the Frappe desk). This page only selects a run,
// renders the proposed rows, and exports them; it never posts to any ledger.

import { useEffect, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { payrollApi } from "@shared/services/api";
import { downloadCsv } from "@shared/services/csv";
import type { PayrollRun, JournalExport } from "@shared/types";

const COLUMNS = [
  { key: "account", header: "الحساب" },
  { key: "description", header: "البيان" },
  { key: "debit", header: "مدين" },
  { key: "credit", header: "دائن" },
];

export default function AccountingJournalPage() {
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [run, setRun] = useState("");
  const [journal, setJournal] = useState<JournalExport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    payrollApi.payrollRuns().then(setRuns).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!run) {
      setJournal(null);
      return;
    }
    setLoading(true);
    setError(null);
    payrollApi
      .journalExport(run)
      .then((j) => setJournal(j))
      .catch((e: Error) => {
        setError(e.message); // e.g. incomplete Payroll Account Mapping
        setJournal(null);
      })
      .finally(() => setLoading(false));
  }, [run]);

  return (
    <div>
      <PageHeader
        title="القيد المحاسبي"
        subtitle="قيد مقترح متوازن من نتائج الرواتب — للعرض والتصدير فقط (لا ترحيل للقيود)"
      />

      <div className="mb-6 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الدورة</span>
          <select
            value={run}
            onChange={(e) => setRun(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            <option value="">— اختر دورة —</option>
            {runs.map((r) => (
              <option key={r.name} value={r.name}>
                {r.name}
              </option>
            ))}
          </select>
        </label>

        <button
          type="button"
          onClick={() =>
            journal &&
            downloadCsv(
              `journal-${run}`,
              journal.rows as unknown as Record<string, unknown>[],
              COLUMNS,
            )
          }
          disabled={!journal || journal.rows.length === 0}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          تنزيل CSV
        </button>
        <button
          type="button"
          onClick={() => window.open(payrollApi.journalExportUrl(run), "_blank")}
          disabled={!journal || journal.rows.length === 0}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          تنزيل Excel
        </button>
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {!run ? (
        <p className="text-sm text-slate-500">اختر دورة رواتب لعرض القيد المقترح.</p>
      ) : null}
      {loading ? <p className="text-sm text-slate-500">جارٍ التحميل…</p> : null}

      {journal && !loading ? (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="px-4 py-3 font-medium">
                      {c.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {journal.rows.length === 0 ? (
                  <tr>
                    <td colSpan={COLUMNS.length} className="px-4 py-6 text-center text-slate-400">
                      لا توجد بيانات.
                    </td>
                  </tr>
                ) : (
                  journal.rows.map((r, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-4 py-3 text-slate-800">{r.account}</td>
                      <td className="px-4 py-3 text-slate-800">{r.description}</td>
                      <td className="px-4 py-3 text-slate-800">
                        <span className="num">{r.debit || ""}</span>
                      </td>
                      <td className="px-4 py-3 text-slate-800">
                        <span className="num">{r.credit || ""}</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm font-medium text-slate-700">
            مدين: <span className="num">{journal.total_debit}</span> | دائن:{" "}
            <span className="num">{journal.total_credit}</span> —{" "}
            {journal.balanced ? "متوازن ✓" : "غير متوازن ✗"}
          </p>
        </>
      ) : null}
    </div>
  );
}
