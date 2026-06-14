"use client";

// Create a Promotion Request (draft). The target grade/stage/salary are computed by
// the promotion engine on approval — never here. RBAC-gated; backend re-enforces.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@shared/components/PageHeader";
import { FormShell } from "@shared/forms/FormShell";
import { Loading } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canManagePayroll } from "@shared/services/roles";
import type { GovernmentEmployeePayrollProfile } from "@shared/types";

export default function NewPromotionPage() {
  const router = useRouter();
  const { roles, loading } = useRoles();
  const mayCreate = canManagePayroll(roles);

  const [employees, setEmployees] = useState<GovernmentEmployeePayrollProfile[] | null>(null);
  const [employee, setEmployee] = useState("");
  const [vacancy, setVacancy] = useState(false);
  const [managerRec, setManagerRec] = useState(false);
  const [committee, setCommittee] = useState("");
  const [remarks, setRemarks] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi.employees().then(setEmployees).catch((e: Error) => setError(e.message));
  }, []);

  async function onSubmit() {
    setBusy(true);
    setError(null);
    try {
      await payrollApi.createPromotionRequest(employee, {
        vacancy_available: vacancy ? 1 : 0,
        direct_manager_recommendation: managerRec ? 1 : 0,
        committee_decision: committee || undefined,
        remarks: remarks || undefined,
      });
      router.push("/government-payroll/promotions");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const inp = "rounded-lg border border-slate-300 px-3 py-2";
  const chk = "h-4 w-4 rounded border-slate-300";

  if (loading) return <Loading />;
  if (!mayCreate) {
    return (
      <div>
        <PageHeader title="إضافة ترفيع" />
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          ليس لديك صلاحية لإنشاء طلبات الترفيع.
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="إضافة طلب ترفيع" subtitle="يُنشأ كمسودة؛ يحتسب المحرك الدرجة والمرحلة والراتب عند الاعتماد" />
      <FormShell title="طلب ترفيع" onSubmit={onSubmit}>
        {error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>
        ) : null}
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الموظف *</span>
          <select required value={employee} onChange={(e) => setEmployee(e.target.value)} className={inp}>
            <option value="">— اختر الموظف —</option>
            {(employees ?? []).map((p) => (
              <option key={p.name} value={p.name}>{p.employee_name} ({p.employee_number})</option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-5 text-sm text-slate-700">
          <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={vacancy} onChange={(e) => setVacancy(e.target.checked)} /> توفر شاغر</label>
          <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={managerRec} onChange={(e) => setManagerRec(e.target.checked)} /> توصية المدير المباشر</label>
        </div>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">قرار اللجنة</span>
          <input value={committee} onChange={(e) => setCommittee(e.target.value)} className={inp} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">ملاحظات</span>
          <textarea value={remarks} onChange={(e) => setRemarks(e.target.value)} className={inp} rows={2} />
        </label>
        <div className="flex items-center gap-3">
          <button type="submit" disabled={busy || !employee}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50">
            {busy ? "…" : "حفظ المسودة"}
          </button>
          <button type="button" onClick={() => router.push("/government-payroll/promotions")}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">إلغاء</button>
        </div>
      </FormShell>
    </div>
  );
}
