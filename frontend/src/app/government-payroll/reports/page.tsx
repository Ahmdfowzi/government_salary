"use client";

// Payroll reports (Phase 4 M10/M11) — read-only. The backend aggregates Salary
// Slip / Snapshot (run reports) or Pension Calculation / Retirement Pension
// Snapshot (pension register). This page only selects inputs, renders the returned
// rows, and exports them client-side as CSV. No calculation or workflow logic.

import { useEffect, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { payrollApi } from "@shared/services/api";
import { downloadCsv } from "@shared/services/csv";
import { useRoles } from "@shared/services/RolesContext";
import { canExportReports } from "@shared/services/roles";
import type { PayrollRun } from "@shared/types";

type Column = { key: string; header: string; numeric?: boolean };
type Renderable = {
  columns: Column[];
  rows: Record<string, unknown>[];
  totalsLine?: string;
  csvName: string;
};

const REPORT_TYPES = [
  { key: "summary", label: "ملخص الدورة" },
  { key: "employee", label: "كشف رواتب الموظفين" },
  { key: "allowances", label: "كشف المخصصات" },
  { key: "deductions", label: "كشف الاستقطاعات" },
  { key: "tax", label: "كشف الضريبة" },
  { key: "bank", label: "تحويل بنكي" },
  { key: "pension", label: "كشف التقاعد" },
] as const;
type ReportKey = (typeof REPORT_TYPES)[number]["key"];
type RunReportKey = Exclude<ReportKey, "pension">;

const PENSION_STATUSES = ["", "Draft", "Calculated", "Approved"];

// Frontend report key -> backend report name (for the Excel export endpoint).
const EXPORT_NAME: Record<ReportKey, string> = {
  summary: "run_summary",
  employee: "employee_register",
  allowances: "allowances_register",
  deductions: "deductions_register",
  tax: "tax_register",
  bank: "bank_transfer",
  pension: "pension_register",
};

const rows = (r: unknown) => r as Record<string, unknown>[];

async function loadRunReport(type: RunReportKey, run: string): Promise<Renderable> {
  switch (type) {
    case "summary": {
      const d = await payrollApi.reportRunSummary(run);
      return {
        columns: [
          { key: "employees", header: "عدد الموظفين", numeric: true },
          { key: "total_basic", header: "الأساسي", numeric: true },
          { key: "total_earnings", header: "الاستحقاقات", numeric: true },
          { key: "total_deductions", header: "الاستقطاعات", numeric: true },
          { key: "total_net", header: "الصافي", numeric: true },
        ],
        rows: [d as unknown as Record<string, unknown>],
        csvName: `run-summary-${run}`,
      };
    }
    case "employee": {
      const d = await payrollApi.reportEmployeeRegister(run);
      return {
        columns: [
          { key: "employee_name", header: "الموظف" },
          { key: "grade_code", header: "الدرجة" },
          { key: "stage", header: "المرحلة", numeric: true },
          { key: "basic", header: "الأساسي", numeric: true },
          { key: "allowances", header: "المخصصات", numeric: true },
          { key: "deductions", header: "الاستقطاعات", numeric: true },
          { key: "net", header: "الصافي", numeric: true },
        ],
        rows: rows(d.rows),
        totalsLine: `الإجمالي — الصافي: ${d.totals.net}`,
        csvName: `employee-register-${run}`,
      };
    }
    case "allowances":
    case "deductions": {
      const d =
        type === "allowances"
          ? await payrollApi.reportAllowances(run)
          : await payrollApi.reportDeductions(run);
      return {
        columns: [
          { key: "employee_name", header: "الموظف" },
          { key: "component_name", header: "المكوّن" },
          { key: "component_code", header: "الرمز" },
          { key: "basis_amount", header: "الأساس", numeric: true },
          { key: "rate", header: "النسبة", numeric: true },
          { key: "amount", header: "المبلغ", numeric: true },
        ],
        rows: rows(d.rows),
        totalsLine: `الإجمالي: ${d.grand_total}`,
        csvName: `${type}-register-${run}`,
      };
    }
    case "tax": {
      const d = await payrollApi.reportTax(run);
      return {
        columns: [
          { key: "employee_name", header: "الموظف" },
          { key: "taxable", header: "الدخل الخاضع", numeric: true },
          { key: "tax", header: "الضريبة", numeric: true },
        ],
        rows: rows(d.rows),
        totalsLine: `إجمالي الضريبة: ${d.total_tax}`,
        csvName: `tax-register-${run}`,
      };
    }
    case "bank": {
      const d = await payrollApi.reportBankTransfer(run);
      const mapped = d.rows.map((r) => ({
        ...r,
        status_text: r.bank_complete ? "مكتمل" : `ناقص: ${r.missing.join("، ")}`,
      }));
      return {
        columns: [
          { key: "employee_profile", header: "الموظف" },
          { key: "employee_name", header: "الاسم" },
          { key: "iban", header: "IBAN" },
          { key: "bank_name", header: "المصرف" },
          { key: "bank_account", header: "رقم الحساب" },
          { key: "national_id", header: "الهوية" },
          { key: "net", header: "الصافي", numeric: true },
          { key: "status_text", header: "الحالة" },
        ],
        rows: rows(mapped),
        totalsLine: `الإجمالي — الصافي: ${d.total_net} | غير مكتمل: ${d.incomplete_count} من ${d.count}`,
        csvName: `bank-transfer-${run}`,
      };
    }
  }
}

async function loadPensionReport(
  from: string,
  to: string,
  status: string,
): Promise<Renderable> {
  const d = await payrollApi.reportPensionRegister(
    from || undefined,
    to || undefined,
    status || undefined,
  );
  return {
    columns: [
      { key: "employee_profile", header: "الموظف" },
      { key: "employee_name", header: "الاسم" },
      { key: "qualification", header: "التحصيل" },
      { key: "service_years", header: "سنوات الخدمة", numeric: true },
      { key: "average_36_months", header: "متوسط ٣٦ شهر", numeric: true },
      { key: "approved_pension", header: "التقاعد المُقَرّ", numeric: true },
      { key: "certificate_allowance", header: "مخصص الشهادة", numeric: true },
      { key: "cost_of_living", header: "غلاء المعيشة", numeric: true },
      { key: "gross_pension", header: "الإجمالي", numeric: true },
      { key: "monthly_tax", header: "الضريبة الشهرية", numeric: true },
      { key: "other_deductions", header: "استقطاعات أخرى", numeric: true },
      { key: "net_pension", header: "الصافي", numeric: true },
      { key: "end_of_service_bonus", header: "مكافأة نهاية الخدمة", numeric: true },
      { key: "status", header: "الحالة" },
      { key: "calculation_date", header: "تاريخ الاحتساب", numeric: true },
    ],
    rows: rows(d.rows),
    totalsLine: `الإجمالي — الصافي: ${d.totals.net_pension ?? 0} (عدد: ${d.count})`,
    csvName: "pension-register",
  };
}

export default function ReportsPage() {
  const { roles } = useRoles();
  const mayExport = canExportReports(roles);
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [run, setRun] = useState("");
  const [type, setType] = useState<ReportKey>("summary");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [status, setStatus] = useState("");
  const [report, setReport] = useState<Renderable | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    payrollApi.payrollRuns().then(setRuns).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    const isPension = type === "pension";
    if (!isPension && !run) {
      setReport(null);
      return;
    }
    setLoading(true);
    setError(null);
    const p = isPension
      ? loadPensionReport(fromDate, toDate, status)
      : loadRunReport(type, run);
    p.then(setReport)
      .catch((e: Error) => {
        setError(e.message);
        setReport(null);
      })
      .finally(() => setLoading(false));
  }, [type, run, fromDate, toDate, status]);

  const isPension = type === "pension";

  return (
    <div>
      <PageHeader
        title="التقارير"
        subtitle="كشوف الرواتب والتقاعد — للعرض والتصدير فقط"
      />

      {/* Controls */}
      <div className="mb-6 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">التقرير</span>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as ReportKey)}
            className="rounded-lg border border-slate-300 px-3 py-2"
          >
            {REPORT_TYPES.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>
        </label>

        {isPension ? (
          <>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-slate-600">من تاريخ</span>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-slate-600">إلى تاريخ</span>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              <span className="text-slate-600">الحالة</span>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="rounded-lg border border-slate-300 px-3 py-2"
              >
                {PENSION_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s || "الكل"}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : (
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
        )}

        {mayExport ? (
          <>
            <button
              type="button"
              onClick={() =>
                report && downloadCsv(report.csvName, report.rows, report.columns)
              }
              disabled={!report || report.rows.length === 0}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              تنزيل CSV
            </button>

            <button
              type="button"
              onClick={() =>
                window.open(
                  payrollApi.exportReportUrl(
                    EXPORT_NAME[type],
                    isPension
                      ? { from_date: fromDate, to_date: toDate, status }
                      : { run },
                    "xlsx",
                  ),
                  "_blank",
                )
              }
              disabled={!report || report.rows.length === 0}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              تنزيل Excel
            </button>

            <button
              type="button"
              onClick={() =>
                window.open(
                  payrollApi.exportReportUrl(
                    EXPORT_NAME[type],
                    isPension
                      ? { from_date: fromDate, to_date: toDate, status }
                      : { run },
                    "pdf",
                  ),
                  "_blank",
                )
              }
              disabled={!report || report.rows.length === 0}
              className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              تنزيل PDF
            </button>
          </>
        ) : null}
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {!isPension && !run ? (
        <p className="text-sm text-slate-500">اختر دورة رواتب لعرض التقرير.</p>
      ) : null}

      {loading ? <p className="text-sm text-slate-500">جارٍ التحميل…</p> : null}

      {report && !loading ? (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  {report.columns.map((c) => (
                    <th key={c.key} className="px-4 py-3 font-medium">
                      {c.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.rows.length === 0 ? (
                  <tr>
                    <td
                      colSpan={report.columns.length}
                      className="px-4 py-6 text-center text-slate-400"
                    >
                      لا توجد بيانات.
                    </td>
                  </tr>
                ) : (
                  report.rows.map((r, i) => (
                    <tr
                      key={i}
                      className={`border-t border-slate-100 ${
                        r["bank_complete"] === false ? "bg-rose-50" : ""
                      }`}
                    >
                      {report.columns.map((c) => (
                        <td key={c.key} className="px-4 py-3 text-slate-800">
                          {c.numeric ? (
                            <span className="num">{String(r[c.key] ?? "")}</span>
                          ) : (
                            String(r[c.key] ?? "")
                          )}
                        </td>
                      ))}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {report.totalsLine ? (
            <p className="mt-3 text-sm font-medium text-slate-700">{report.totalsLine}</p>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
