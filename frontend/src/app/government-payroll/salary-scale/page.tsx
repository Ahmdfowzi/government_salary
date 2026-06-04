import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// SalaryScale — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function SalaryScalePage() {
  return (
    <div>
      <PageHeader title="سلم الرواتب" subtitle="جدول الدرجات والمراحل (Government Salary Scale)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
