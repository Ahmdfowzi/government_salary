"use client";

// Allowance Rules — earnings/deductions components and how they are matched and
// valued. Read-only list from the Frappe DocType.

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { SearchInput } from "@shared/components/SearchInput";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { DataTable, type Column } from "@shared/tables/DataTable";
import { payrollApi } from "@shared/services/api";
import type { AllowanceRule } from "@shared/types";

function value(a: AllowanceRule): string {
  if (a.calculation_type === "Percentage") return a.percentage != null ? `${a.percentage}%` : "—";
  return a.fixed_amount != null ? a.fixed_amount.toLocaleString("en-US") : "—";
}

const columns: Column<AllowanceRule>[] = [
  { key: "code", header: "الرمز", numeric: true, render: (a) => a.component_code },
  { key: "name", header: "المكوّن", render: (a) => a.component_name },
  {
    key: "type",
    header: "النوع",
    render: (a) => (
      <Pill tone={a.allowance_type === "Deduction" ? "danger" : "success"}>
        {a.allowance_type === "Deduction" ? "استقطاع" : "مخصص"}
      </Pill>
    ),
  },
  { key: "context", header: "السياق", render: (a) => a.context },
  { key: "match", header: "المطابقة", render: (a) => `${a.match_key ?? "—"}${a.match_value ? ` · ${a.match_value}` : ""}` },
  { key: "value", header: "القيمة", numeric: true, render: (a) => value(a) },
  { key: "cap", header: "سقف 200%", render: (a) => a.capped_under_200 ?? "—" },
  {
    key: "active",
    header: "الحالة",
    render: (a) => <Pill tone={a.is_active ? "success" : "neutral"}>{a.is_active ? "فعّالة" : "غير فعّالة"}</Pill>,
  },
];

export default function AllowancesPage() {
  const [list, setList] = useState<AllowanceRule[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    payrollApi.allowances().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  const rows = useMemo(() => {
    const items = list ?? [];
    const term = q.trim().toLowerCase();
    if (!term) return items;
    return items.filter((a) =>
      [a.component_code, a.component_name, a.match_value, a.rule_set]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(term)),
    );
  }, [list, q]);

  return (
    <div>
      <PageHeader title="المخصصات" subtitle="قواعد المخصصات والاستقطاعات (Allowance Rule)" />
      <div className="mb-6">
        <SearchInput value={q} onChange={setQ} placeholder="بحث بالمكوّن أو القيمة…" />
      </div>
      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : rows.length === 0 ? (
        <Empty message="لا توجد قواعد مخصصات." />
      ) : (
        <>
          <DataTable columns={columns} rows={rows} rowKey={(a) => a.name} />
          <p className="mt-3 text-xs text-slate-400">
            عدد القواعد: <span className="num">{rows.length}</span>
          </p>
        </>
      )}
    </div>
  );
}
