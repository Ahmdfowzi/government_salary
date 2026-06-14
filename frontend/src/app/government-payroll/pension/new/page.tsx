"use client";

// Create a Pension Calculation. The figures are computed by the EXISTING pension
// engine on the backend (no math here); the form collects the inputs and shows the
// stored result. RBAC-gated; backend re-enforces.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { FormShell } from "@shared/forms/FormShell";
import { Loading } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canManagePayroll } from "@shared/services/roles";
import type { GovernmentEmployeePayrollProfile, PensionCalcResult } from "@shared/types";

export default function NewPensionPage() {
  const router = useRouter();
  const { roles, loading } = useRoles();
  const mayCreate = canManagePayroll(roles);

  const [employees, setEmployees] = useState<GovernmentEmployeePayrollProfile[] | null>(null);
  const [f, setF] = useState<Record<string, string>>({
    employee_profile: "", service_years: "", extra_months: "0", average_36_months: "",
    last_functional_salary: "", last_full_salary: "", other_deductions: "0",
    calculation_date: "", remarks: "",
  });
  const set = (k: string, v: string) => setF((s) => ({ ...s, [k]: v }));
  const [result, setResult] = useState<PensionCalcResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi.employees().then(setEmployees).catch((e: Error) => setError(e.message));
  }, []);

  const required = f.employee_profile && f.service_years && f.average_36_months && f.last_functional_salary;

  async function onSubmit() {
    setBusy(true);
    setError(null);
    try {
      const r = await payrollApi.createPensionCalculation({
        employee_profile: f.employee_profile,
        service_years: Number(f.service_years),
        average_36_months: Number(f.average_36_months),
        last_functional_salary: Number(f.last_functional_salary),
        last_full_salary: f.last_full_salary ? Number(f.last_full_salary) : undefined,
        extra_months: f.extra_months ? Number(f.extra_months) : 0,
        other_deductions: f.other_deductions ? Number(f.other_deductions) : 0,
        calculation_date: f.calculation_date || undefined,
        remarks: f.remarks || undefined,
      });
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const inp = "rounded-lg border border-slate-300 px-3 py-2";
  const money = (n: number) => n?.toLocaleString("en-US");

  if (loading) return <Loading />;
  if (!mayCreate) {
    return (
      <div>
        <PageHeader title="احتساب تقاعد" />
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          ليس لديك صلاحية لاحتساب التقاعد.
        </div>
      </div>
    );
  }

  if (result) {
    return (
      <div>
        <PageHeader title="نتيجة احتساب التقاعد" subtitle={result.name} />
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {[
              ["الراتب التقاعدي المقرّر", result.approved_pension],
              ["مخصصات الشهادة", result.certificate_allowance],
              ["مخصص غلاء المعيشة", result.cost_of_living],
              ["إجمالي التقاعد", result.gross_pension],
              ["ضريبة التقاعد", result.monthly_tax],
              ["مكافأة نهاية الخدمة", result.end_of_service_bonus],
            ].map(([label, val]) => (
              <div key={label as string} className="rounded-lg border border-slate-200 p-3">
                <p className="text-xs text-slate-500">{label as string}</p>
                <p className="num mt-0.5 text-lg font-bold text-slate-900">{money(val as number)}</p>
              </div>
            ))}
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
              <p className="text-xs text-emerald-700">صافي التقاعد</p>
              <p className="num mt-0.5 text-xl font-bold text-emerald-700">{money(result.net_pension)}</p>
            </div>
          </div>
          {result.warnings?.length ? (
            <ul className="mt-4 list-disc rounded-lg border border-amber-200 bg-amber-50 p-3 pr-6 text-xs text-amber-800">
              {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          ) : null}
          <div className="mt-5 flex gap-3">
            <Link href="/government-payroll/pension" className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">إلى كشف التقاعد</Link>
            <button onClick={() => { setResult(null); }} className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">احتساب آخر</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="احتساب تقاعد" subtitle="تُحتسب القيم على الخادم بمحرك التقاعد القانوني" />
      <FormShell title="مدخلات احتساب التقاعد" onSubmit={onSubmit}>
        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
        ) : null}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">الموظف *</span>
            <select required value={f.employee_profile} onChange={(e) => set("employee_profile", e.target.value)} className={inp}>
              <option value="">— اختر الموظف —</option>
              {(employees ?? []).map((p) => (
                <option key={p.name} value={p.name}>{p.employee_name} ({p.employee_number})</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">سنوات الخدمة *</span>
            <input type="number" min={0} value={f.service_years} onChange={(e) => set("service_years", e.target.value)} className={`${inp} num`} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">أشهر إضافية</span>
            <input type="number" min={0} value={f.extra_months} onChange={(e) => set("extra_months", e.target.value)} className={`${inp} num`} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">معدل آخر 36 شهراً *</span>
            <input type="number" min={0} value={f.average_36_months} onChange={(e) => set("average_36_months", e.target.value)} className={`${inp} num`} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">آخر راتب اسمي *</span>
            <input type="number" min={0} value={f.last_functional_salary} onChange={(e) => set("last_functional_salary", e.target.value)} className={`${inp} num`} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">آخر راتب كلي (لمكافأة نهاية الخدمة)</span>
            <input type="number" min={0} value={f.last_full_salary} onChange={(e) => set("last_full_salary", e.target.value)} className={`${inp} num`} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">استقطاعات أخرى</span>
            <input type="number" min={0} value={f.other_deductions} onChange={(e) => set("other_deductions", e.target.value)} className={`${inp} num`} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">تاريخ الاحتساب</span>
            <input type="date" value={f.calculation_date} onChange={(e) => set("calculation_date", e.target.value)} className={`${inp} num`} />
          </label>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">ملاحظات</span>
          <textarea value={f.remarks} onChange={(e) => set("remarks", e.target.value)} className={inp} rows={2} />
        </label>
        <div className="flex items-center gap-3">
          <button type="submit" disabled={busy || !required}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50">
            {busy ? "…" : "احتساب وحفظ"}
          </button>
          <button type="button" onClick={() => router.push("/government-payroll/pension")}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">إلغاء</button>
        </div>
      </FormShell>
    </div>
  );
}
