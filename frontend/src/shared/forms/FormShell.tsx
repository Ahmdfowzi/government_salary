// Layout shell for data-entry forms (Phase 2 fills the fields).
// IMPORTANT: forms only collect/submit data — they never compute salary values.

export function FormShell({
  title,
  children,
  onSubmit,
}: {
  title: string;
  children?: React.ReactNode;
  onSubmit?: () => void;
}) {
  return (
    <form
      className="rounded-xl border border-slate-200 bg-white p-6"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.();
      }}
    >
      <h2 className="mb-4 text-lg font-semibold text-slate-900">{title}</h2>
      <div className="flex flex-col gap-4">{children}</div>
    </form>
  );
}
