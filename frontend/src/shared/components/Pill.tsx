// Small generic status pill (read-only/edit badge, lock indicator, balance, etc.).

type Tone = "neutral" | "info" | "success" | "warn" | "danger" | "dark";

const TONES: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-600 ring-slate-200",
  info: "bg-sky-100 text-sky-700 ring-sky-200",
  success: "bg-emerald-100 text-emerald-700 ring-emerald-200",
  warn: "bg-amber-100 text-amber-800 ring-amber-200",
  danger: "bg-rose-100 text-rose-700 ring-rose-200",
  dark: "bg-slate-800 text-white ring-slate-700",
};

export function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: Tone;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${TONES[tone]}`}
    >
      {children}
    </span>
  );
}
