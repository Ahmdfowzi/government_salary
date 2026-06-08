"use client";

// Employee Payroll Profiles — searchable list with in-app create/edit (Phase 5
// M5). Create/edit is RBAC-gated in the UI and re-enforced by the backend; no
// Frappe Desk needed. No destructive actions are offered here.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { SearchInput } from "@shared/components/SearchInput";
import { Pill } from "@shared/components/Pill";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canWriteProfiles } from "@shared/services/roles";
import type { GovernmentEmployeePayrollProfile } from "@shared/types";

export default function EmployeesPage() {
  const { roles } = useRoles();
  const mayWrite = canWriteProfiles(roles);
  const [list, setList] = useState<GovernmentEmployeePayrollProfile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.employees().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    const items = list ?? [];
    const term = q.trim().toLowerCase();
    if (!term) return items;
    return items.filter((e) =>
      [e.employee_number, e.employee_name, e.government_entity, e.grade]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(term)),
    );
  }, [list, q]);

  return (
    <div>
      <PageHeader
        title="الموظفون"
        subtitle="الملفات الراتبية للموظفين (Government Employee Payroll Profile)"
      />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالاسم أو الرقم أو الجهة…" />
        <div className="flex items-center gap-3">
          <Pill tone={mayWrite ? "info" : "neutral"}>
            {mayWrite ? "وضع التحرير متاح" : "للعرض فقط"}
          </Pill>
          {mayWrite ? (
            <Link
              href="/government-payroll/employees/new"
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700"
            >
              + إضافة موظف
            </Link>
          ) : null}
        </div>
      </div>

      {error ? <ErrorBanner message={error} /> : null}

      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد نتائج." />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">الرقم</th>
                  <th className="px-4 py-3 font-medium">الاسم</th>
                  <th className="px-4 py-3 font-medium">الجهة</th>
                  <th className="px-4 py-3 font-medium">الحالة</th>
                  <th className="px-4 py-3 font-medium">الدرجة</th>
                  <th className="px-4 py-3 font-medium">المرحلة</th>
                  <th className="px-4 py-3 font-medium">الأساسي</th>
                  <th className="px-4 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((e) => (
                  <tr key={e.name} className="border-t border-slate-100 hover:bg-slate-50">
                    <td className="px-4 py-3 num text-slate-800">{e.employee_number}</td>
                    <td className="px-4 py-3 font-medium text-slate-900">{e.employee_name}</td>
                    <td className="px-4 py-3 text-slate-600">{e.government_entity ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-600">{e.status}</td>
                    <td className="px-4 py-3 num text-slate-800">{e.grade ?? "—"}</td>
                    <td className="px-4 py-3 num text-slate-800">{e.current_stage}</td>
                    <td className="px-4 py-3 num text-slate-800">{e.basic_salary ?? ""}</td>
                    <td className="px-4 py-3">
                      {mayWrite ? (
                        <Link
                          href={`/government-payroll/employees/${encodeURIComponent(e.name)}/edit`}
                          className="text-sky-700 hover:underline"
                        >
                          تعديل
                        </Link>
                      ) : (
                        <span className="text-slate-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            عدد الموظفين: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
