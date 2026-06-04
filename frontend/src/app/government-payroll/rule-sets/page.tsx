import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// RuleSets — placeholder route. Data list / forms arrive in a later milestone.
export default function RuleSetsPage() {
  return (
    <div>
      <PageHeader title="مجموعات القواعد" subtitle="نسخ حزم القواعد القانونية (Government Rule Set)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
