import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// SalaryLaws — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function SalaryLawsPage() {
  return (
    <div>
      <PageHeader title="قوانين الرواتب" subtitle="إدارة نسخ قوانين/سلالم الرواتب (Government Salary Law)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
