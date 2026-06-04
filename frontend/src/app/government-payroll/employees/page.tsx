import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// Employees — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function EmployeesPage() {
  return (
    <div>
      <PageHeader title="الموظفون" subtitle="الملفات الراتبية للموظفين (Employee Payroll Profile)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
