// Color-coded workflow-state pill for Payroll Run governance. Display-only: the
// state value is decided entirely by the backend; this just maps it to an Arabic
// label and a color. Unknown states fall back to a neutral style.

interface StateStyle {
  label: string;
  className: string;
}

const STATE_STYLES: Record<string, StateStyle> = {
  Draft: { label: "مسودة", className: "bg-slate-100 text-slate-700 ring-slate-200" },
  Calculated: { label: "محتسبة", className: "bg-sky-100 text-sky-700 ring-sky-200" },
  "Under Review": { label: "قيد المراجعة", className: "bg-amber-100 text-amber-800 ring-amber-200" },
  Approved: { label: "معتمدة", className: "bg-blue-100 text-blue-700 ring-blue-200" },
  Submitted: { label: "مُقدّمة", className: "bg-emerald-100 text-emerald-700 ring-emerald-200" },
  Locked: { label: "مقفلة", className: "bg-slate-800 text-white ring-slate-700" },
  Cancelled: { label: "ملغاة", className: "bg-rose-100 text-rose-700 ring-rose-200" },
};

const FALLBACK: StateStyle = {
  label: "",
  className: "bg-slate-100 text-slate-600 ring-slate-200",
};

export function StateBadge({ state }: { state: string }) {
  const style = STATE_STYLES[state] ?? { ...FALLBACK, label: state };
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset ${style.className}`}
    >
      {style.label || state}
    </span>
  );
}
