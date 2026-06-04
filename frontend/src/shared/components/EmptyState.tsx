// Placeholder used by Phase 1 route pages where the full UI lands in Phase 2.

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
      <p>{message}</p>
      <p className="mt-2 text-xs text-slate-400">
        ستُبنى الواجهة الكاملة في المرحلة الثانية — جميع الحسابات في الخادم فقط.
      </p>
    </div>
  );
}
