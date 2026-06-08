"use client";

// Promotion Requests — read-only list from the Frappe DocType. Grades are
// Government Grade Links (from → to); promotion advances grade + stage.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { DataTable, type Column } from "@shared/tables/DataTable";
import { payrollApi } from "@shared/services/api";
import type { PromotionRequest } from "@shared/types";

function statusTone(s: string): "success" | "danger" | "neutral" | "warn" {
  if (s === "Approved" || s === "Applied") return "success";
  if (s === "Rejected") return "danger";
  if (s === "Draft") return "neutral";
  return "warn";
}

const columns: Column<PromotionRequest>[] = [
  { key: "request", header: "الطلب", numeric: true, render: (r) => r.name },
  { key: "employee", header: "الموظف", render: (r) => r.employee_name ?? r.employee_profile },
  {
    key: "grade",
    header: "الدرجة (من → إلى)",
    numeric: true,
    render: (r) => `${r.from_grade_ref ?? "—"} → ${r.to_grade_ref ?? "—"}`,
  },
  { key: "stage", header: "المرحلة المقترحة", numeric: true, render: (r) => r.proposed_stage ?? "—" },
  { key: "years", header: "سنوات الدرجة", numeric: true, render: (r) => r.years_in_grade ?? "—" },
  { key: "old_salary", header: "الراتب القديم", numeric: true, render: (r) => r.old_salary?.toLocaleString("en-US") ?? "—" },
  { key: "new_salary", header: "الراتب الجديد", numeric: true, render: (r) => r.new_salary?.toLocaleString("en-US") ?? "—" },
  { key: "status", header: "الحالة", render: (r) => <Pill tone={statusTone(r.approval_status)}>{r.approval_status}</Pill> },
];

export default function PromotionsPage() {
  const [list, setList] = useState<PromotionRequest[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.promotions().then(setList).catch((e: Error) => setError(e.message));
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
      <PageHeader title="الترفيعات" subtitle="طلبات الترفيع (Promotion Request)" />
      <div className="mb-6">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالموظف أو الطلب…" />
      </div>
      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد طلبات ترفيع." />
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
