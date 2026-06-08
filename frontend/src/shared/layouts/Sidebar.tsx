"use client";

// RTL navigation sidebar for the Government Payroll module. Role-aware: items with
// a `requires` predicate are hidden when the current user lacks the capability
// (a UX convenience — the backend still enforces every restriction).

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRoles } from "@shared/services/RolesContext";
import { canExportJournal } from "@shared/services/roles";

export interface NavItem {
  href: string;
  label: string;
  requires?: (roles: string[]) => boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/government-payroll", label: "لوحة التحكم" },
  { href: "/government-payroll/payroll-runs", label: "دورات الرواتب" },
  { href: "/government-payroll/employees", label: "الموظفون" },
  { href: "/government-payroll/reports", label: "التقارير" },
  { href: "/government-payroll/pension", label: "كشف التقاعد" },
  { href: "/government-payroll/accounting-journal", label: "القيد المحاسبي", requires: canExportJournal },
  { href: "/government-payroll/rule-sets", label: "مجموعات القواعد" },
  { href: "/government-payroll/salary-scale", label: "سلم الرواتب" },
  { href: "/government-payroll/allowances", label: "المخصصات" },
  { href: "/government-payroll/increments", label: "العلاوات السنوية" },
  { href: "/government-payroll/promotions", label: "الترفيعات" },
  { href: "/government-payroll/calculation-logs", label: "سجلات الاحتساب" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { roles } = useRoles();
  const items = NAV_ITEMS.filter((i) => !i.requires || i.requires(roles));

  return (
    <aside className="w-64 shrink-0 border-l border-slate-200 bg-white p-4">
      <div className="mb-6 px-2">
        <p className="text-sm font-bold text-slate-900">رواتب موظفي الدولة</p>
        <p className="text-xs text-slate-400">النظام الحكومي العراقي</p>
      </div>
      <nav className="flex flex-col gap-1">
        {items.map((item) => {
          const active =
            item.href === "/government-payroll"
              ? pathname === item.href
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-sky-50 font-semibold text-sky-700"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
