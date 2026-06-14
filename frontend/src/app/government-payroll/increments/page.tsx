"use client";

// Annual Increment Requests — read-only list from the Frappe DocType. Grade is
// the Government Grade Link; increments advance only the stage.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { DataTable, type Column } from "@shared/tables/DataTable";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";
import { canManagePayroll } from "@shared/services/roles";
import type { AnnualIncrementRequest } from "@shared/types";

function statusTone(s: string): "success" | "danger" | "neutral" | "warn" {
  if (s === "Approved" || s === "Applied") return "success";
  if (s === "Rejected") return "danger";
  if (s === "Draft") return "neutral";
  return "warn";
}

const columns: Column<AnnualIncrementRequest>[] = [
  { key: "request", header: "الطلب", numeric: true, render: (r) => r.name },
  { key: "employee", header: "الموظف", render: (r) => r.employee_name ?? r.employee_profile },
  { key: "grade", header: "الدرجة", numeric: true, render: (r) => r.current_grade_ref ?? "—" },
  {
    key: "stage",
    header: "المرحلة",
    numeric: true,
    render: (r) => `${r.current_stage ?? "—"}${r.new_stage != null ? ` → ${r.new_stage}` : ""}`,
  },
  { key: "cur_salary", header: "الراتب الحالي", numeric: true, render: (r) => r.current_salary?.toLocaleString("en-US") ?? "—" },
  { key: "new_salary", header: "الراتب الجديد", numeric: true, render: (r) => r.new_salary?.toLocaleString("en-US") ?? "—" },
  { key: "amount", header: "مقدار العلاوة", numeric: true, render: (r) => r.increment_amount?.toLocaleString("en-US") ?? "—" },
  { key: "due", header: "تاريخ الاستحقاق", numeric: true, render: (r) => r.due_date ?? "—" },
  { key: "status", header: "الحالة", render: (r) => <Pill tone={statusTone(r.approval_status)}>{r.approval_status}</Pill> },
];

export default function IncrementsPage() {
  const { roles } = useRoles();
  const [list, setList] = useState<AnnualIncrementRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.increments().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    const items = list ?? [];
    const term = q.trim().toLowerCase();
    if (!term) return items;
    return items.filter((r) =>
      [r.name, r.employee_name, r.employee_profile].filter(Boolean).some((v) => String(v).toLowerCase().includes(term)),
    );
  }, [list, q]);

  return (
    <div>
      <PageHeader title="العلاوات السنوية" subtitle="طلبات العلاوة السنوية (Annual Increment Request)" />
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالموظف أو الطلب…" />
        {canManagePayroll(roles) ? (
          <Link href="/government-payroll/increments/new" className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700">+ إضافة علاوة</Link>
        ) : null}
      </div>
      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد طلبات علاوة." />
      ) : (
        <>
          <DataTable columns={columns} rows={rows} rowKey={(r) => r.name} />
          <p className="mt-3 text-xs text-slate-400">
            عدد الطلبات: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
