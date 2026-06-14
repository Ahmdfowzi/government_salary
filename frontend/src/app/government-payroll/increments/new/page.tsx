"use client";

// Create an Annual Increment Request (draft). The new stage/salary are computed by
// the increment engine on approval — never here. RBAC-gated; backend re-enforces.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { PageHeader } from "@shared/components/PageHeader";
import { FormShell } from "@shared/forms/FormShell";
import { Loading } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canManagePayroll } from "@shared/services/roles";
import type { GovernmentEmployeePayrollProfile } from "@shared/types";

export default function NewIncrementPage() {
  const router = useRouter();
  const { roles, loading } = useRoles();
  const mayCreate = canManagePayroll(roles);

  const [employees, setEmployees] = useState<GovernmentEmployeePayrollProfile[] | null>(null);
  const [employee, setEmployee] = useState("");
  const [dueDate, setDueDate] = useState("");
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
      await payrollApi.createIncrementRequest(employee, dueDate || undefined, remarks || undefined);
      router.push("/government-payroll/increments");
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  const inp = "rounded-lg border border-slate-300 px-3 py-2";

  if (loading) return <Loading />;
  if (!mayCreate) {
    return (
      <div>
        <PageHeader title="إضافة علاوة سنوية" />
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          ليس لديك صلاحية لإنشاء طلبات العلاوة.
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="إضافة طلب علاوة سنوية" subtitle="يُنشأ كمسودة؛ يحتسب المحرك المرحلة والراتب عند الاعتماد" />
      <FormShell title="طلب علاوة سنوية" onSubmit={onSubmit}>
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
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">تاريخ الاستحقاق</span>
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className={`${inp} num`} />
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
          <button type="button" onClick={() => router.push("/government-payroll/increments")}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">إلغاء</button>
        </div>
      </FormShell>
    </div>
  );
}
