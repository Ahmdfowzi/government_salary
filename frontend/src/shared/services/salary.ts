// Salary-scale loader. The scale (grade/stage -> basic salary) lives in the
// `details` child table of Government Salary Scale, which the list API does not
// return — so we fetch each scale doc. Used to render the Salary Scale page and
// to resolve an employee's basic salary from the SAME source the engine uses
// (no computation in the frontend — these are stored fixture values).

import { payrollApi } from "./api";
import type { GovernmentSalaryScale, GovernmentSalaryScaleDetail } from "../types";

export interface ScaleData {
  scales: GovernmentSalaryScale[];
  /** Stored basic salary for (rule_set, grade, stage), or undefined if absent. */
  basic: (ruleSet?: string, grade?: string, stage?: number) => number | undefined;
}

export async function loadScales(): Promise<ScaleData> {
  const list = await payrollApi.salaryScales();
  const docs = await Promise.all(list.map((s) => payrollApi.salaryScale(s.name)));
  const map = new Map<string, number>();
  for (const d of docs) {
    for (const det of d.details ?? []) {
      const grade = det.grade_code ?? String(det.grade);
      map.set(`${d.rule_set}|${grade}|${det.stage}`, det.basic_salary);
    }
  }
  return {
    scales: docs,
    basic: (rs, g, st) =>
      g != null && st != null ? map.get(`${rs}|${g}|${st}`) : undefined,
  };
}

export type { GovernmentSalaryScaleDetail };
