"use client";

// Salary Calculation (preview). Resolves the basic salary for a (rule set, grade,
// stage) from the backend — the SAME engine resolver payroll uses. No math here.
// Full payroll calculation (allowances/tax/pension/net) runs from Payroll Runs.

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@shared/components/PageHeader";
import { payrollApi } from "@shared/services/api";
import type { GovernmentGradeOption, GovernmentRuleSet, SalaryPreview } from "@shared/types";

export default function SalaryCalculationPage() {
  const [grades, setGrades] = useState<GovernmentGradeOption[]>([]);
  const [ruleSets, setRuleSets] = useState<GovernmentRuleSet[]>([]);
  const [ruleSet, setRuleSet] = useState("");
  const [grade, setGrade] = useState("");
  const [stage, setStage] = useState("");
  const [preview, setPreview] = useState<SalaryPreview | null>(null);

  useEffect(() => {
    payrollApi.grades().then(setGrades).catch(() => {});
    payrollApi.ruleSets().then((r) => {
      setRuleSets(r);
      const active = r.find((x) => x.status === "Active");
      if (active) setRuleSet(active.name);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!ruleSet || !grade || !stage) { setPreview(null); return; }
    let cancelled = false;
    payrollApi.salaryPreview(ruleSet, grade, stage)
      .then((r) => !cancelled && setPreview(r))
      .catch(() => !cancelled && setPreview(null));
    return () => { cancelled = true; };
  }, [ruleSet, grade, stage]);

  const gradeLabel = useMemo(() => {
    const m = new Map(grades.map((g) => [g.grade_code, g] as const));
    return (c: string) => { const g = m.get(c); return g ? `${g.grade_code}${g.grade_name_ar ? " — " + g.grade_name_ar : ""}` : c; };
  }, [grades]);

  const inp = "rounded-lg border border-slate-300 px-3 py-2";

  return (
    <div>
      <PageHeader title="احتساب الراتب" subtitle="معاينة الراتب الأساسي حسب الدرجة والمرحلة (من سلم الرواتب الفعّال)" />

      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">مجموعة القواعد</span>
            <select value={ruleSet} onChange={(e) => setRuleSet(e.target.value)} className={inp}>
              <option value="">— اختر —</option>
              {ruleSets.map((r) => <option key={r.name} value={r.name}>{r.name}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">الدرجة</span>
            <select value={grade} onChange={(e) => setGrade(e.target.value)} className={inp}>
              <option value="">— اختر الدرجة —</option>
              {grades.map((g) => <option key={g.grade_code} value={g.grade_code}>{gradeLabel(g.grade_code)}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="text-slate-600">المرحلة</span>
            <input type="number" min={1} value={stage} onChange={(e) => setStage(e.target.value)} className={`${inp} num`} />
          </label>
        </div>

        <div className="mt-5">
          {preview ? (
            preview.valid ? (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-sm text-emerald-700">الراتب الأساسي</p>
                <p className="num mt-1 text-2xl font-bold text-emerald-700">{preview.basic_salary?.toLocaleString("en-US")} <span className="text-base font-normal">دينار</span></p>
              </div>
            ) : (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{preview.message}</div>
            )
          ) : (
            <p className="text-sm text-slate-400">اختر مجموعة القواعد والدرجة والمرحلة لعرض الراتب الأساسي.</p>
          )}
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-500">
        هذه معاينة للراتب الأساسي فقط. يتم احتساب الراتب الكامل (المخصصات، الضريبة، التقاعد، الصافي) ضمن{" "}
        <Link href="/government-payroll/payroll-runs" className="text-sky-700 hover:underline">دورات الرواتب</Link>.
      </p>
    </div>
  );
}
