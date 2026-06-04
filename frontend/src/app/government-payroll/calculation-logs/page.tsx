import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// CalculationLogs — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function CalculationLogsPage() {
  return (
    <div>
      <PageHeader title="سجلات الاحتساب" subtitle="سجل التدقيق غير القابل للتعديل (Salary Calculation Log)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
