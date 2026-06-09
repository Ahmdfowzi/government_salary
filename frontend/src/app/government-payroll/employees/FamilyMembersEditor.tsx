"use client";

// Family & Dependents editor (Phase 5 M7) — create/edit/delete dependents with
// live summary cards. PREVIEW counts are computed client-side; the backend
// recomputes ages/eligibility/counts authoritatively on save.

import { useMemo } from "react";
import { summarizeFamily, computeAge, isEligible, DEFAULT_FAMILY_CONFIG } from "@shared/services/family";
import type { FamilyMemberDependent, FamilyRelation } from "@shared/types";

const RELATIONS: FamilyRelation[] = ["Spouse", "Son", "Daughter", "Father", "Mother", "Other"];
const RELATION_AR: Record<FamilyRelation, string> = {
  Spouse: "زوج/زوجة", Son: "ابن", Daughter: "ابنة", Father: "أب", Mother: "أم", Other: "آخر",
};
const EMPLOYMENT = ["None", "Government", "Private", "Contract"];
const EDU = ["", "None", "Primary", "Intermediate", "Secondary", "Diploma", "Bachelor", "Higher Diploma", "Master", "Doctorate"];

const blank = (): FamilyMemberDependent => ({
  full_name: "", relation: "Son", is_alive: 1, financially_dependent: 1, employment_type: "None",
});

function Card({ label, value, accent = "text-slate-900" }: { label: string; value: number; accent?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`num mt-0.5 text-xl font-bold ${accent}`}>{value}</p>
    </div>
  );
}

export function FamilyMembersEditor({
  members,
  onChange,
}: {
  members: FamilyMemberDependent[];
  onChange: (next: FamilyMemberDependent[]) => void;
}) {
  const summary = useMemo(() => summarizeFamily(members), [members]);

  function update(i: number, patch: Partial<FamilyMemberDependent>) {
    onChange(members.map((m, idx) => (idx === i ? { ...m, ...patch } : m)));
  }
  function remove(i: number) {
    onChange(members.filter((_, idx) => idx !== i));
  }

  const chk = "h-4 w-4 rounded border-slate-300";
  const inp = "rounded-lg border border-slate-300 px-2 py-1.5 text-sm";

  return (
    <div className="flex flex-col gap-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card label="الزوج/الزوجة" value={summary.spouse_count} />
        <Card label="الأبناء" value={summary.children_count} />
        <Card label="الأبناء المستحقون" value={summary.eligible_children_count} accent="text-emerald-600" />
        <Card label="المعالون" value={summary.dependents_count} />
        <Card label="المعالون المستحقون" value={summary.eligible_dependents_count} accent="text-emerald-600" />
        <Card label="ذوو الإعاقة" value={summary.disabled_dependents_count} />
        <Card label="الموظفون" value={summary.employed_dependents_count} accent="text-amber-600" />
        <Card label="الطلبة" value={summary.student_dependents_count} />
      </div>

      {/* Member cards */}
      {members.map((m, i) => {
        const age = computeAge(m.date_of_birth);
        const eligible = isEligible(m, age, DEFAULT_FAMILY_CONFIG);
        return (
          <div key={i} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-700">
                {m.full_name || "فرد جديد"}{age != null ? ` · العمر ` : ""}
                {age != null ? <span className="num">{age}</span> : null}
                {eligible ? <span className="mr-2 rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700">مستحق</span> : null}
              </span>
              <button type="button" onClick={() => remove(i)} className="text-xs text-rose-600 hover:underline">
                حذف
              </button>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">الاسم الكامل *</span>
                <input value={m.full_name} onChange={(e) => update(i, { full_name: e.target.value })} className={inp} />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">صلة القرابة *</span>
                <select value={m.relation} onChange={(e) => update(i, { relation: e.target.value as FamilyRelation })} className={inp}>
                  {RELATIONS.map((r) => <option key={r} value={r}>{RELATION_AR[r]}</option>)}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">الجنس</span>
                <select value={m.gender ?? ""} onChange={(e) => update(i, { gender: e.target.value as FamilyMemberDependent["gender"] })} className={inp}>
                  <option value="">—</option><option value="Male">ذكر</option><option value="Female">أنثى</option>
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">تاريخ الميلاد</span>
                <input type="date" value={m.date_of_birth ?? ""} onChange={(e) => update(i, { date_of_birth: e.target.value })} className={`${inp} num`} />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">نوع التوظيف</span>
                <select value={m.employment_type ?? "None"} onChange={(e) => update(i, { employment_type: e.target.value as FamilyMemberDependent["employment_type"] })} className={inp}>
                  {EMPLOYMENT.map((x) => <option key={x} value={x}>{x === "None" ? "لا يعمل" : x}</option>)}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">الدخل الشهري</span>
                <input type="number" min={0} value={m.monthly_income ?? ""} onChange={(e) => update(i, { monthly_income: e.target.value ? Number(e.target.value) : undefined })} className={`${inp} num`} />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">المستوى التعليمي</span>
                <select value={m.education_level ?? ""} onChange={(e) => update(i, { education_level: e.target.value })} className={inp}>
                  {EDU.map((x) => <option key={x} value={x}>{x || "—"}</option>)}
                </select>
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">نوع الإعاقة</span>
                <input value={m.disability_type ?? ""} onChange={(e) => update(i, { disability_type: e.target.value })} className={inp} />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="text-slate-600">ملاحظات</span>
                <input value={m.notes ?? ""} onChange={(e) => update(i, { notes: e.target.value })} className={inp} />
              </label>
            </div>

            <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-700">
              <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={Boolean(Number(m.is_alive ?? 1))} onChange={(e) => update(i, { is_alive: e.target.checked ? 1 : 0 })} /> على قيد الحياة</label>
              <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={Boolean(Number(m.financially_dependent ?? 1))} onChange={(e) => update(i, { financially_dependent: e.target.checked ? 1 : 0 })} /> معال مالياً</label>
              <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={Boolean(Number(m.is_employed))} onChange={(e) => update(i, { is_employed: e.target.checked ? 1 : 0 })} /> يعمل</label>
              <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={Boolean(Number(m.is_student))} onChange={(e) => update(i, { is_student: e.target.checked ? 1 : 0 })} /> طالب</label>
              <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={Boolean(Number(m.has_disability))} onChange={(e) => update(i, { has_disability: e.target.checked ? 1 : 0 })} /> لديه إعاقة</label>
              <label className="flex items-center gap-2"><input type="checkbox" className={chk} checked={Boolean(Number(m.legal_guardianship))} onChange={(e) => update(i, { legal_guardianship: e.target.checked ? 1 : 0 })} /> وصاية قانونية</label>
            </div>
          </div>
        );
      })}

      <div>
        <button
          type="button"
          onClick={() => onChange([...members, blank()])}
          className="rounded-lg border border-sky-300 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700 hover:bg-sky-100"
        >
          + إضافة فرد
        </button>
      </div>
    </div>
  );
}
