// Frontend mirror of services/family/family_service — PREVIEW ONLY. The backend
// recomputes ages/eligibility/counts authoritatively on save; this just powers the
// live summary cards while editing. Keep the rules in sync with the Python service.

import type { FamilyMemberDependent, FamilySummary } from "../types";

const CHILD_RELATIONS = ["Son", "Daughter"];

export interface FamilyConfig {
  childMaxAge: number;
  studentMaxAge: number;
  incomeThreshold: number;
}
export const DEFAULT_FAMILY_CONFIG: FamilyConfig = {
  childMaxAge: 18,
  studentMaxAge: 24,
  incomeThreshold: 0,
};

const truthy = (v: unknown, dflt = false): boolean =>
  v === undefined || v === null || v === "" ? dflt : Boolean(Number(v) || v === true);

export function computeAge(dob?: string, asOf?: Date): number | null {
  if (!dob) return null;
  const b = new Date(dob);
  if (Number.isNaN(b.getTime())) return null;
  const ref = asOf ?? new Date();
  let age = ref.getFullYear() - b.getFullYear();
  const m = ref.getMonth() - b.getMonth();
  if (m < 0 || (m === 0 && ref.getDate() < b.getDate())) age -= 1;
  return Math.max(0, age);
}

function selfSupporting(m: FamilyMemberDependent, cfg: FamilyConfig): boolean {
  const employed = truthy(m.is_employed) || (m.employment_type && m.employment_type !== "None");
  return Boolean(employed) && Number(m.monthly_income || 0) > cfg.incomeThreshold;
}

export function isEligible(m: FamilyMemberDependent, age: number | null, cfg: FamilyConfig): boolean {
  if (!truthy(m.is_alive, true)) return false;
  if (!truthy(m.financially_dependent, true)) return false;
  if (selfSupporting(m, cfg)) return false;
  if (truthy(m.has_disability)) return true;
  if (CHILD_RELATIONS.includes(m.relation)) {
    if (age === null) return false;
    if (age <= cfg.childMaxAge) return true;
    return truthy(m.is_student) && age <= cfg.studentMaxAge;
  }
  return true;
}

export function summarizeFamily(
  members: FamilyMemberDependent[],
  cfg: FamilyConfig = DEFAULT_FAMILY_CONFIG,
  asOf?: Date,
): FamilySummary {
  const s: FamilySummary = {
    spouse_count: 0, children_count: 0, eligible_children_count: 0, dependents_count: 0,
    eligible_dependents_count: 0, disabled_dependents_count: 0,
    employed_dependents_count: 0, student_dependents_count: 0,
  };
  for (const m of members) {
    const age = computeAge(m.date_of_birth, asOf);
    const alive = truthy(m.is_alive, true);
    const isChild = CHILD_RELATIONS.includes(m.relation);
    const eligible = isEligible(m, age, cfg);
    if (m.relation === "Spouse" && alive) s.spouse_count += 1;
    if (isChild) s.children_count += 1;
    if (isChild && eligible) s.eligible_children_count += 1;
    if (alive && truthy(m.financially_dependent, true)) s.dependents_count += 1;
    if (eligible) s.eligible_dependents_count += 1;
    if (truthy(m.has_disability)) s.disabled_dependents_count += 1;
    if (truthy(m.is_employed)) s.employed_dependents_count += 1;
    if (truthy(m.is_student)) s.student_dependents_count += 1;
  }
  return s;
}
