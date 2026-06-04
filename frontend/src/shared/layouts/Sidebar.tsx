// RTL navigation sidebar for the Government Payroll module.
// Single source of truth for the route list (mirrors the app router folders).

import Link from "next/link";

export interface NavItem {
  href: string;
  label: string;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/government-payroll", label: "الرئيسية" },
  { href: "/government-payroll/salary-laws", label: "قوانين الرواتب" },
  { href: "/government-payroll/salary-scale", label: "سلم الرواتب" },
  { href: "/government-payroll/employees", label: "الموظفون" },
  { href: "/government-payroll/allowances", label: "المخصصات" },
  { href: "/government-payroll/increments", label: "العلاوات السنوية" },
  { href: "/government-payroll/promotions", label: "الترفيعات" },
  { href: "/government-payroll/pension", label: "التقاعد" },
  { href: "/government-payroll/calculation-logs", label: "سجلات الاحتساب" },
];

export function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-l border-slate-200 bg-white p-4">
      <div className="mb-6 px-2">
        <p className="text-sm font-bold text-slate-900">رواتب موظفي الدولة</p>
        <p className="text-xs text-slate-400">النظام الحكومي</p>
      </div>
      <nav className="flex flex-col gap-1">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
