"use client";

// Session gate. Frappe enforces all permissions and the frontend talks to it
// over the same-origin proxy, so a session must exist on THIS origin. The Frappe
// Desk cookie (on the bench host) is not shared here, and there is no other way
// in; this minimal login establishes the session, then the app renders. Not a
// business feature — it is the auth plumbing the data pages require.

import { useState } from "react";
import { payrollApi } from "@shared/services/api";
import { useRoles } from "@shared/services/RolesContext";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { authenticated, loading, refresh } = useRoles();
  const [usr, setUsr] = useState("");
  const [pwd, setPwd] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-400">
        جارٍ التحميل…
      </div>
    );
  }
  if (authenticated) return <>{children}</>;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await payrollApi.login(usr.trim(), pwd);
      await refresh();
    } catch (err) {
      setError((err as Error).message || "تعذّر تسجيل الدخول.");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <h1 className="mb-1 text-lg font-semibold text-slate-900">تسجيل الدخول</h1>
        <p className="mb-5 text-xs text-slate-500">
          نظام رواتب موظفي الدولة العراقية — يتطلب جلسة دخول إلى Frappe.
        </p>

        {error ? (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <label className="mb-3 flex flex-col gap-1 text-sm">
          <span className="text-slate-600">اسم المستخدم أو البريد</span>
          <input
            required
            value={usr}
            onChange={(e) => setUsr(e.target.value)}
            autoComplete="username"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="mb-5 flex flex-col gap-1 text-sm">
          <span className="text-slate-600">كلمة المرور</span>
          <input
            required
            type="password"
            value={pwd}
            onChange={(e) => setPwd(e.target.value)}
            autoComplete="current-password"
            className="rounded-lg border border-slate-300 px-3 py-2 num"
          />
        </label>

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "…" : "دخول"}
        </button>
      </form>
    </div>
  );
}
