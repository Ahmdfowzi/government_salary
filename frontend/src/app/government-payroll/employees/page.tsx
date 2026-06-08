"use client";

// Employee Payroll Profiles — searchable read-only list. Edit opens the Frappe
// desk form and is labelled per role (the desk re-enforces permissions). No
// destructive actions are offered here for any role.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canEditProfiles } from "@shared/services/roles";
import type { GovernmentEmployeePayrollProfile } from "@shared/types";

const DESK_BASE =
  (process.env.NEXT_PUBLIC_FRAPPE_BASE_URL ?? "http://localhost:8000") +
  "/app/government-employee-payroll-profile/";

export default function EmployeesPage() {
  const { roles } = useRoles();
  const mayEdit = canEditProfiles(roles);
  const [list, setList] = useState<GovernmentEmployeePayrollProfile[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi
      .employees()
      .then(setList)
      .catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    const items = list ?? [];
    const term = q.trim().toLowerCase();
    if (!term) return items;
    return items.filter((e) =>
      [e.employee_number, e.employee_name, e.government_entity, e.grade_code]
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

      <div className="mb-6">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="بحث بالاسم أو الرقم أو الجهة…"
          className="w-full max-w-md rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {list === null && !error ? (
        <p className="text-sm text-slate-500">جارٍ التحميل…</p>
      ) : rows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          لا توجد نتائج.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-right text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">الرقم</th>
                <th className="px-4 py-3 font-medium">الاسم</th>
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
                  <td className="px-4 py-3 text-slate-900">{e.employee_name}</td>
                  <td className="px-4 py-3 text-slate-600">{e.status}</td>
                  <td className="px-4 py-3 num text-slate-800">{e.grade_code ?? e.current_grade}</td>
                  <td className="px-4 py-3 num text-slate-800">{e.current_stage}</td>
                  <td className="px-4 py-3 num text-slate-800">{e.basic_salary ?? ""}</td>
                  <td className="px-4 py-3">
                    <a
                      href={DESK_BASE + encodeURIComponent(e.name)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sky-700 hover:underline"
                    >
                      {mayEdit ? "عرض / تعديل" : "عرض"}
                    </a>
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
