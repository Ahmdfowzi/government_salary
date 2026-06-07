// Typed API surface for the Government Payroll module.
// Maps UI sections to Frappe DocTypes / whitelisted methods.
// Phase 2 M1: declares the data contract (read-only lists). Calculation
// endpoints remain backend-only placeholders — no math in the frontend.

import { getList, getDoc, callMethod } from "./frappeClient";
import type {
  GovernmentRuleSet,
  GovernmentSalaryScale,
  GovernmentEntity,
  GovernmentPosition,
  GovernmentEmployeePayrollProfile,
  QualificationAppointmentRule,
  AllowanceRule,
  IncomeTaxBracket,
  TaxAllowanceRule,
  PensionRule,
  PromotionRule,
  AnnualIncrementRule,
  GeographicArea,
  AnnualIncrementRequest,
  PromotionRequest,
  PensionCalculation,
  PayrollPeriod,
  PayrollRun,
  SalarySlip,
  EmployeeMonthlySalary,
  PayrollCalculationSnapshot,
  RunGovernance,
} from "../types";

const API = "iraqi_government_payroll.iraqi_government_payroll.api.payroll_api";

export const payrollApi = {
  // Versioning spine + rule members
  ruleSets: () => getList<GovernmentRuleSet>("Government Rule Set"),
  salaryScales: () => getList<GovernmentSalaryScale>("Government Salary Scale"),
  qualificationRules: () =>
    getList<QualificationAppointmentRule>("Qualification Appointment Rule"),
  allowances: () => getList<AllowanceRule>("Allowance Rule"),
  incomeTaxBrackets: () => getList<IncomeTaxBracket>("Income Tax Bracket"),
  taxAllowanceRules: () => getList<TaxAllowanceRule>("Tax Allowance Rule"),
  pensionRules: () => getList<PensionRule>("Pension Rule"),
  promotionRules: () => getList<PromotionRule>("Promotion Rule"),
  annualIncrementRules: () => getList<AnnualIncrementRule>("Annual Increment Rule"),
  geographicAreas: () => getList<GeographicArea>("Geographic Area"),

  // Organization
  entities: () => getList<GovernmentEntity>("Government Entity"),
  positions: () => getList<GovernmentPosition>("Government Position"),

  // Employee
  employees: () =>
    getList<GovernmentEmployeePayrollProfile>("Government Employee Payroll Profile"),
  getEmployee: (name: string) =>
    getDoc<GovernmentEmployeePayrollProfile>("Government Employee Payroll Profile", name),
  monthlySalaries: () => getList<EmployeeMonthlySalary>("Employee Monthly Salary"),

  // Transactions
  increments: () => getList<AnnualIncrementRequest>("Annual Increment Request"),
  promotions: () => getList<PromotionRequest>("Promotion Request"),
  pensions: () => getList<PensionCalculation>("Pension Calculation"),

  // Operational
  payrollPeriods: () => getList<PayrollPeriod>("Payroll Period"),
  payrollRuns: () => getList<PayrollRun>("Payroll Run"),
  salarySlips: () => getList<SalarySlip>("Salary Slip"),

  // Audit / reproducibility
  snapshots: () => getList<PayrollCalculationSnapshot>("Payroll Calculation Snapshot"),

  // Payroll Run governance (Phase 3 M6/M7). The backend is authoritative for
  // state, permissions and the audit trail; the UI only renders what these return.
  runGovernance: (run: string) =>
    callMethod<RunGovernance>(`${API}.get_run_governance`, { run }),
  runAction: (run: string, action: string) =>
    callMethod<Pick<RunGovernance, "name" | "workflow_state" | "allowed_actions">>(
      `${API}.run_governance_action`,
      { run, action },
    ),
  createRun: (
    period: string,
    rule_set: string,
    scope: string,
    scope_reference?: string,
  ) =>
    callMethod<Pick<RunGovernance, "name" | "workflow_state" | "allowed_actions">>(
      `${API}.create_payroll_run`,
      { period, rule_set, scope, scope_reference },
    ),

  // Calculation triggers — backend only (implemented in later milestones).
  calculateActiveSalary: (profile: string, period_date: string) =>
    callMethod(`${API}.calculate_active_salary`, { profile, period_date }),
  evaluateIncrement: (profile: string) =>
    callMethod(`${API}.evaluate_increment`, { profile }),
  evaluatePromotion: (profile: string) =>
    callMethod(`${API}.evaluate_promotion`, { profile }),
  computePension: (profile: string, calculation_date: string) =>
    callMethod(`${API}.compute_pension`, { profile, calculation_date }),
};
