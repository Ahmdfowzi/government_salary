import { PageHeader } from "@shared/components/PageHeader";
import { EmptyState } from "@shared/components/EmptyState";

// Promotions — Phase 1 placeholder route. Data list / forms arrive in Phase 2.
export default function PromotionsPage() {
  return (
    <div>
      <PageHeader title="الترفيعات" subtitle="طلبات الترفيع (Promotion Request)" />
      <EmptyState message="هذه الصفحة جاهزة كهيكل في المرحلة الأولى." />
    </div>
  );
}
