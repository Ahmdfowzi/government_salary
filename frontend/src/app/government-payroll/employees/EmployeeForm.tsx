"use client";

// Employee Payroll Profile create/edit form (Phase 5 M5).
//
// Transport + presentation ONLY. No salary math here: the basic-salary preview
// and the (grade, stage) validity come from the backend (salary_preview), and the
// save goes through save_employee_profile which re-validates and enforces RBAC.
// The form uses the Government Grade Link master — never the deprecated grade_code.

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { FormShell } from "@shared/forms/FormShell";
import { payrollApi } from "@shared/services/api";
import { FamilyMembersEditor } from "./FamilyMembersEditor";
import type {
  GovernmentEmployeePayrollProfile,
  GovernmentGradeOption,
  GovernmentEntity,
  GovernmentPosition,
  GovernmentRuleSet,
  SalaryPreview,
  FamilyMemberDependent,
} from "@shared/types";

const QUALIFICATIONS = [
  "Primary", "Secondary", "Diploma", "Bachelor",
  "Higher Diploma", "Master", "Doctorate", "Trade / Craft",
];
const STATUSES = ["Active", "Suspended", "Retired", "Transferred"];
const MARITAL = ["Single", "Married", "Divorced", "Widowed"];

// Editable string-keyed field state (numbers are parsed at submit time).
type FormState = Record<string, string>;

const FIELDS: (keyof GovernmentEmployeePayrollProfile)[] = [
  "employee_number", "employee_name", "status", "rule_set",
  "government_entity", "government_position", "grade", "current_stage",
  "qualification", "marital_status", "appointment_date", "appointment_grade_ref",
  "appointment_stage", "bank_account", "bank_name", "iban", "national_id",
];

function fromProfile(p?: GovernmentEmployeePayrollProfile): FormState {
  const s: FormState = {};
  for (const f of FIELDS) s[f] = p?.[f] != null ? String(p[f]) : "";
  if (!p) s.status = "Active";
  return s;
}

export function EmployeeForm({
  mode,
  initial,
}: {
  mode: "create" | "edit";
  initial?: GovernmentEmployeePayrollProfile;
}) {
  const router = useRouter();

  const [form, setForm] = useState<FormState>(() => fromProfile(initial));
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const [tab, setTab] = useState<"basic" | "family">("basic");
  const [members, setMembers] = useState<FamilyMemberDependent[]>(
    () => initial?.family_members ?? [],
  );

  // Master data
  const [grades, setGrades] = useState<GovernmentGradeOption[]>([]);
  const [entities, setEntities] = useState<GovernmentEntity[]>([]);
  const [positions, setPositions] = useState<GovernmentPosition[]>([]);
  const [ruleSets, setRuleSets] = useState<GovernmentRuleSet[]>([]);

  // Salary preview / validity
  const [preview, setPreview] = useState<SalaryPreview | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    payrollApi.grades().then(setGrades).catch(() => {});
    payrollApi.entities().then(setEntities).catch(() => {});
    payrollApi.positions().then(setPositions).catch(() => {});
    payrollApi.ruleSets().then(setRuleSets).catch(() => {});
  }, []);

  // Live basic-salary preview whenever (rule_set, grade, current_stage) are all set.
  const { rule_set, grade, current_stage } = form;
  useEffect(() => {
    if (!rule_set || !grade || !current_stage) {
      setPreview(null);
      return;
    }
    let cancelled = false;
    payrollApi
      .salaryPreview(rule_set, grade, current_stage)
      .then((r) => !cancelled && setPreview(r))
      .catch(() => !cancelled && setPreview(null));
    return () => {
      cancelled = true;
    };
  }, [rule_set, grade, current_stage]);

  const requiredMissing = !form.employee_number || !form.employee_name
    || !form.rule_set || !form.grade || !form.current_stage;
  const placementInvalid = preview != null && !preview.valid;
  const canSubmit = !requiredMissing && !placementInvalid && !saving;

  const gradeLabel = useMemo(() => {
    const m = new Map(grades.map((g) => [g.grade_code, g] as const));
    return (code: string) => {
      const g = m.get(code);
      return g ? `${g.grade_code}${g.grade_name_ar ? " — " + g.grade_name_ar : ""}` : code;
    };
  }, [grades]);

  async function onSubmit() {
    setSaving(true);
    setSaveError(null);
    try {
      const payload: Partial<GovernmentEmployeePayrollProfile> = {
        employee_name: form.employee_name,
        status: form.status as GovernmentEmployeePayrollProfile["status"],
        rule_set: form.rule_set,
        government_entity: form.government_entity || undefined,
        government_position: form.government_position || undefined,
        grade: form.grade,
        current_stage: Number(form.current_stage),
        qualification: form.qualification || undefined,
        appointment_date: form.appointment_date || undefined,
        appointment_grade_ref: form.appointment_grade_ref || undefined,
        appointment_stage: form.appointment_stage ? Number(form.appointment_stage) : undefined,
        marital_status: (form.marital_status as GovernmentEmployeePayrollProfile["marital_status"]) || undefined,
        bank_account: form.bank_account || undefined,
        bank_name: form.bank_name || undefined,
        iban: form.iban || undefined,
        national_id: form.national_id || undefined,
        family_members: members.filter((m) => m.full_name.trim()),
      };
      if (mode === "create") payload.employee_number = form.employee_number;
      const saved = await payrollApi.saveEmployeeProfile(
        payload,
        mode === "edit" ? initial!.name : undefined,
      );
      router.push(`/government-payroll/employees?saved=${encodeURIComponent(saved.name)}`);
    } catch (e) {
      setSaveError((e as Error).message);
      setSaving(false);
    }
  }

  const inputCls = "rounded-lg border border-slate-300 px-3 py-2";

  return (
    <FormShell
      title={mode === "create" ? "إضافة موظف جديد" : `تعديل الموظف: ${initial?.employee_name ?? ""}`}
      onSubmit={onSubmit}
    >
      {saveError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {saveError}
        </div>
      ) : null}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {([["basic", "البيانات الأساسية"], ["family", "العائلة والمعالون"]] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === id ? "border-sky-600 text-sky-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {label}
            {id === "family" && members.length ? <span className="num mr-1 text-xs text-slate-400"> ({members.length})</span> : null}
          </button>
        ))}
      </div>

      <div className={tab === "basic" ? "grid grid-cols-1 gap-4 sm:grid-cols-2" : "hidden"}>
        {/* Identity */}
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الرقم الوظيفي *</span>
          <input
            required
            value={form.employee_number}
            onChange={(e) => set("employee_number", e.target.value)}
            disabled={mode === "edit"}
            className={`${inputCls} num disabled:bg-slate-100 disabled:text-slate-500`}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">اسم الموظف *</span>
          <input
            required
            value={form.employee_name}
            onChange={(e) => set("employee_name", e.target.value)}
            className={inputCls}
          />
        </label>

        {/* Org */}
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الجهة الحكومية</span>
          <select value={form.government_entity} onChange={(e) => set("government_entity", e.target.value)} className={inputCls}>
            <option value="">— بدون —</option>
            {entities.map((o) => (<option key={o.name} value={o.name}>{o.entity_name_ar ?? o.name}</option>))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">المنصب</span>
          <select value={form.government_position} onChange={(e) => set("government_position", e.target.value)} className={inputCls}>
            <option value="">— بدون —</option>
            {positions.map((o) => (<option key={o.name} value={o.name}>{o.position_name_ar ?? o.name}</option>))}
          </select>
        </label>

        {/* Rule set + grade + stage */}
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">مجموعة القواعد *</span>
          <select required value={form.rule_set} onChange={(e) => set("rule_set", e.target.value)} className={inputCls}>
            <option value="">— اختر —</option>
            {ruleSets.map((o) => (<option key={o.name} value={o.name}>{o.name}</option>))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الدرجة *</span>
          <select required value={form.grade} onChange={(e) => set("grade", e.target.value)} className={inputCls}>
            <option value="">— اختر الدرجة —</option>
            {grades.map((g) => (<option key={g.grade_code} value={g.grade_code}>{gradeLabel(g.grade_code)}</option>))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">المرحلة الحالية *</span>
          <input
            required type="number" min={1}
            value={form.current_stage}
            onChange={(e) => set("current_stage", e.target.value)}
            className={`${inputCls} num`}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">التحصيل الدراسي</span>
          <select value={form.qualification} onChange={(e) => set("qualification", e.target.value)} className={inputCls}>
            <option value="">— بدون —</option>
            {QUALIFICATIONS.map((q) => (<option key={q} value={q}>{q}</option>))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الحالة الاجتماعية</span>
          <select value={form.marital_status} onChange={(e) => set("marital_status", e.target.value)} className={inputCls}>
            <option value="">— بدون —</option>
            {MARITAL.map((mstat) => (<option key={mstat} value={mstat}>{mstat}</option>))}
          </select>
        </label>

        {/* Appointment */}
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">تاريخ التعيين</span>
          <input type="date" value={form.appointment_date} onChange={(e) => set("appointment_date", e.target.value)} className={`${inputCls} num`} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">درجة التعيين</span>
          <select value={form.appointment_grade_ref} onChange={(e) => set("appointment_grade_ref", e.target.value)} className={inputCls}>
            <option value="">— بدون —</option>
            {grades.map((g) => (<option key={g.grade_code} value={g.grade_code}>{gradeLabel(g.grade_code)}</option>))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">مرحلة التعيين</span>
          <input type="number" min={1} value={form.appointment_stage} onChange={(e) => set("appointment_stage", e.target.value)} className={`${inputCls} num`} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الحالة *</span>
          <select required value={form.status} onChange={(e) => set("status", e.target.value)} className={inputCls}>
            {STATUSES.map((s) => (<option key={s} value={s}>{s}</option>))}
          </select>
        </label>

        {/* Bank info */}
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">رقم الحساب المصرفي</span>
          <input value={form.bank_account} onChange={(e) => set("bank_account", e.target.value)} className={`${inputCls} num`} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">اسم المصرف</span>
          <input value={form.bank_name} onChange={(e) => set("bank_name", e.target.value)} className={inputCls} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">IBAN</span>
          <input value={form.iban} onChange={(e) => set("iban", e.target.value)} className={`${inputCls} num`} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-slate-600">الرقم الوطني</span>
          <input value={form.national_id} onChange={(e) => set("national_id", e.target.value)} className={`${inputCls} num`} />
        </label>
      </div>

      {/* Family & Dependents tab */}
      {tab === "family" ? (
        <FamilyMembersEditor members={members} onChange={setMembers} />
      ) : null}

      {/* Salary preview / placement validity */}
      {tab === "basic" && preview ? (
        preview.valid ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
            الراتب الأساسي للدرجة والمرحلة المختارة:{" "}
            <span className="num font-semibold">
              {preview.basic_salary?.toLocaleString("en-US")}
            </span>{" "}
            دينار
          </div>
        ) : (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {preview.message}
          </div>
        )
      ) : null}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "…" : mode === "create" ? "حفظ الموظف" : "حفظ التعديلات"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/government-payroll/employees")}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
        >
          إلغاء
        </button>
        {requiredMissing ? (
          <span className="text-xs text-slate-400">الحقول المطلوبة: الرقم، الاسم، مجموعة القواعد، الدرجة، المرحلة</span>
        ) : null}
      </div>
    </FormShell>
  );
}
