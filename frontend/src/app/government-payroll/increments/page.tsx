import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// Increments — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function IncrementsPage() {
  return (
    <div>
      <PageHeader title="العلاوات السنوية" subtitle="طلبات العلاوة السنوية (Annual Increment Request)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
