"use client";

// Government Rule Sets — versioned legal rule packages (active + archived).
// Read-only list from the Frappe DocType.

import { useEffect, useState } from "react";
import { PageHeader } from "@shared/components/PageHeader";
import { Pill } from "@shared/components/Pill";
import { Loading, ErrorBanner, Empty } from "@shared/components/States";
import { DataTable, type Column } from "@shared/tables/DataTable";
import { payrollApi } from "@shared/services/api";
import type { GovernmentRuleSet, RuleStatus } from "@shared/types";

const STATUS_TONE: Record<RuleStatus, "success" | "neutral" | "warn"> = {
  Active: "success",
  Archived: "neutral",
  Draft: "warn",
};
const STATUS_AR: Record<RuleStatus, string> = {
  Active: "فعّالة",
  Archived: "مؤرشفة",
  Draft: "مسودة",
};

const columns: Column<GovernmentRuleSet>[] = [
  { key: "code", header: "الرمز", numeric: true, render: (r) => r.rule_set_code ?? r.name },
  { key: "name", header: "الاسم", render: (r) => r.rule_set_name ?? "—" },
  { key: "year", header: "السنة", numeric: true, render: (r) => r.year ?? "—" },
  { key: "from", header: "من تاريخ", numeric: true, render: (r) => r.effective_from ?? "—" },
  { key: "to", header: "إلى تاريخ", numeric: true, render: (r) => r.effective_to ?? "—" },
  {
    key: "status",
    header: "الحالة",
    render: (r) => <Pill tone={STATUS_TONE[r.status] ?? "neutral"}>{STATUS_AR[r.status] ?? r.status}</Pill>,
  },
];

export default function RuleSetsPage() {
  const [list, setList] = useState<GovernmentRuleSet[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi.ruleSets().then(setList).catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div>
      <PageHeader title="مجموعات القواعد" subtitle="نسخ حزم القواعد القانونية (Government Rule Set)" />
      {error ? <ErrorBanner message={error} /> : null}
      {list === null && !error ? (
        <Loading />
      ) : (list ?? []).length === 0 ? (
        <Empty message="لا توجد مجموعات قواعد." />
      ) : (
        <DataTable columns={columns} rows={list ?? []} rowKey={(r) => r.name} />
      )}
    </div>
  );
}
