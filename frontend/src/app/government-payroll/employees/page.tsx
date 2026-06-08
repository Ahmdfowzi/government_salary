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
import { DataTable, type Column } from "@shared/tables/DataTable";
import { payrollApi } from "@shared/services/api";
import { loadScales, type ScaleData } from "@shared/services/salary";
import { useRoles } from "@shared/services/RolesContext";
import { canWriteProfiles } from "@shared/services/roles";
import type { GovernmentEmployeePayrollProfile } from "@shared/types";

export default function EmployeesPage() {
  const { roles } = useRoles();
  const mayWrite = canWriteProfiles(roles);
  const [list, setList] = useState<GovernmentEmployeePayrollProfile[] | null>(null);
  const [scale, setScale] = useState<ScaleData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.employees().then(setList).catch((e: Error) => setError(e.message));
    // Basic salary is resolved from the salary scale (the engine's source); the
    // profile field is not always populated.
    loadScales().then(setScale).catch(() => setScale(null));
  }, []);

  function basicOf(e: GovernmentEmployeePayrollProfile): number | undefined {
    if (e.basic_salary) return e.basic_salary;
    return scale?.basic(e.rule_set, e.grade, e.current_stage);
  }

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

  const columns: Column<GovernmentEmployeePayrollProfile>[] = [
    { key: "number", header: "الرقم", numeric: true, render: (e) => e.employee_number },
    { key: "name", header: "الاسم", render: (e) => e.employee_name },
    { key: "entity", header: "الجهة", render: (e) => e.government_entity ?? "—" },
    { key: "status", header: "الحالة", render: (e) => e.status },
    { key: "grade", header: "الدرجة", numeric: true, render: (e) => e.grade ?? "—" },
    { key: "stage", header: "المرحلة", numeric: true, render: (e) => e.current_stage },
    { key: "basic", header: "الأساسي", numeric: true, render: (e) => basicOf(e)?.toLocaleString("en-US") ?? "—" },
    {
      key: "actions",
      header: "",
      render: (e) =>
        mayWrite ? (
          <Link
            href={`/government-payroll/employees/${encodeURIComponent(e.name)}/edit`}
            className="text-sky-700 hover:underline"
          >
            تعديل
          </Link>
        ) : (
          <span className="text-slate-300">—</span>
        ),
    },
  ];

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
          <DataTable columns={columns} rows={rows} rowKey={(e) => e.name} />
          <p className="mt-3 text-xs text-slate-400">
            عدد الموظفين: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
