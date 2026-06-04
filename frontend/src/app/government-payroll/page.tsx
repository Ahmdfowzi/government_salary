import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { NAV_ITEMS } from "@shared/layouts/Sidebar";

// Module landing page — a simple index of sections (NOT a dashboard).
export default function GovernmentPayrollHome() {
  const sections = NAV_ITEMS.filter((i) => i.href !== "/government-payroll");
  return (
    <div>
      <PageHeader
        title="نظام رواتب موظفي الدولة العراقية"
        subtitle="المرحلة الأولى: هيكلة فقط — جميع الحسابات تتم في الخادم (Python)."
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map((s) => (
          <Link
            key={s.href}
            href={s.href}
            className="rounded-xl border border-slate-200 bg-white p-5 hover:border-slate-300 hover:shadow-sm"
          >
            <span className="text-base font-semibold text-slate-900">{s.label}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
