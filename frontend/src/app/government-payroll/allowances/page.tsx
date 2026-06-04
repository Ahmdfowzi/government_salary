import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// Allowances — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function AllowancesPage() {
  return (
    <div>
      <PageHeader title="المخصصات" subtitle="قواعد المخصصات والاستقطاعات (Allowance Rule)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
