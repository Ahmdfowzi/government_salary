"use client";

// Pension Register (Phase 4 M11 report) — read-only, filtered by date range +
// status. CSV/Excel/PDF exports are shown only to roles allowed to export.

import { useEffect, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { payrollApi } from "@shared/services/api";
import { downloadCsv } from "@shared/services/csv";
import { useRoles } from "@shared/services/RolesContext";
import { canExportReports } from "@shared/services/roles";
import type { PensionRegisterReport } from "@shared/types";

const COLUMNS = [
  { key: "employee_profile", header: "الموظف" },
  { key: "employee_name", header: "الاسم" },
  { key: "qualification", header: "التحصيل" },
  { key: "service_years", header: "سنوات الخدمة" },
  { key: "average_36_months", header: "متوسط ٣٦ شهر" },
  { key: "approved_pension", header: "التقاعد المُقَرّ" },
  { key: "certificate_allowance", header: "مخصص الشهادة" },
  { key: "cost_of_living", header: "غلاء المعيشة" },
  { key: "gross_pension", header: "الإجمالي" },
  { key: "monthly_tax", header: "الضريبة الشهرية" },
  { key: "other_deductions", header: "استقطاعات أخرى" },
  { key: "net_pension", header: "الصافي" },
  { key: "end_of_service_bonus", header: "مكافأة نهاية الخدمة" },
  { key: "status", header: "الحالة" },
  { key: "calculation_date", header: "تاريخ الاحتساب" },
];
const NUMERIC = new Set([
  "service_years", "average_36_months", "approved_pension", "certificate_allowance",
  "cost_of_living", "gross_pension", "monthly_tax", "other_deductions", "net_pension",
  "end_of_service_bonus", "calculation_date",
]);
const STATUSES = ["", "Draft", "Calculated", "Approved"];

export default function PensionPage() {
  const { roles } = useRoles();
  const mayExport = canExportReports(roles);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [status, setStatus] = useState("");
  const [data, setData] = useState<PensionRegisterReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    payrollApi
      .reportPensionRegister(fromDate || undefined, toDate || undefined, status || undefined)
      .then((d) => setData(d))
      .catch((e: Error) => {
        setError(e.message);
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [fromDate, toDate, status]);

  const pdfUrl = () =>
    payrollApi.exportReportUrl(
      "pension_register",
      { from_date: fromDate, to_date: toDate, status },
      "pdf",
    );
  const xlsxUrl = () =>
    payrollApi.exportReportUrl(
      "pension_register",
      { from_date: fromDate, to_date: toDate, status },
      "xlsx",
    );

  return (
    <div>
      <PageHeader title="كشف التقاعد" subtitle="سجل الرواتب التقاعدية — للعرض والتصدير فقط" />

      <div className="mb-6 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">من تاريخ</span>
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">إلى تاريخ</span>
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الحالة</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-2">
            {STATUSES.map((s) => (
              <option key={s} value={s}>{s || "الكل"}</option>
            ))}
          </select>
        </label>

        {mayExport ? (
          <>
            <button type="button"
              onClick={() => data && downloadCsv("pension-register", data.rows as unknown as Record<string, unknown>[], COLUMNS)}
              disabled={!data || data.rows.length === 0}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50">
              تنزيل CSV
            </button>
            <button type="button" onClick={() => window.open(xlsxUrl(), "_blank")}
              disabled={!data || data.rows.length === 0}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50">
              تنزيل Excel
            </button>
            <button type="button" onClick={() => window.open(pdfUrl(), "_blank")}
              disabled={!data || data.rows.length === 0}
              className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50">
              تنزيل PDF
            </button>
          </>
        ) : null}
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>
      ) : null}
      {loading ? <p className="text-sm text-slate-500">جارٍ التحميل…</p> : null}

      {data && !loading ? (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  {COLUMNS.map((c) => (
                    <th key={c.key} className="whitespace-nowrap px-3 py-3 font-medium">{c.header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.length === 0 ? (
                  <tr>
                    <td colSpan={COLUMNS.length} className="px-4 py-6 text-center text-slate-400">
                      لا توجد بيانات.
                    </td>
                  </tr>
                ) : (
                  data.rows.map((r, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      {COLUMNS.map((c) => {
                        const v = (r as unknown as Record<string, unknown>)[c.key];
                        return (
                          <td key={c.key} className="whitespace-nowrap px-3 py-3 text-slate-800">
                            {NUMERIC.has(c.key) ? <span className="num">{String(v ?? "")}</span> : String(v ?? "")}
                          </td>
                        );
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-sm font-medium text-slate-700">
            عدد المتقاعدين: <span className="num">{data.count}</span>
          </p>
        </>
      ) : null}
    </div>
  );
}
