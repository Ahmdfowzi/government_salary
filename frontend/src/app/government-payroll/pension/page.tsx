import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// Pension — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function PensionPage() {
  return (
    <div>
      <PageHeader title="التقاعد" subtitle="احتساب الراتب التقاعدي (Pension Calculation)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
