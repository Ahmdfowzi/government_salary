// Typed API surface for the Government Payroll module.
// Maps UI sections to Frappe DocTypes / whitelisted methods.
// Phase 1: declares the contract. Pages stay placeholders until Phase 2 wiring.

import { getList, getDoc, callMethod } from "./frappeClient";
import type {
  GovernmentSalaryLaw,
  GovernmentSalaryScale,
  GovernmentEmployeePayrollProfile,
  AllowanceRule,
  AnnualIncrementRequest,
  PromotionRequest,
  PensionCalculation,
  SalaryCalculationLog,
} from "../types";

const API = "iraqi_government_payroll.iraqi_government_payroll.api.payroll_api";

export const payrollApi = {
  salaryLaws: () => getList<GovernmentSalaryLaw>("Government Salary Law"),
  salaryScales: () => getList<GovernmentSalaryScale>("Government Salary Scale"),
  employees: () =>
    getList<GovernmentEmployeePayrollProfile>("Government Employee Payroll Profile"),
  allowances: () => getList<AllowanceRule>("Allowance Rule"),
  increments: () => getList<AnnualIncrementRequest>("Annual Increment Request"),
  promotions: () => getList<PromotionRequest>("Promotion Request"),
  pensions: () => getList<PensionCalculation>("Pension Calculation"),
  calculationLogs: () => getList<SalaryCalculationLog>("Salary Calculation Log"),

  getEmployee: (name: string) =>
    getDoc<GovernmentEmployeePayrollProfile>("Government Employee Payroll Profile", name),

  // Calculation triggers — these run on the backend only (Phase 2).
  calculateActiveSalary: (profile: string, period_date: string) =>
    callMethod(`${API}.calculate_active_salary`, { profile, period_date }),
  evaluateIncrement: (profile: string) =>
    callMethod(`${API}.evaluate_increment`, { profile }),
  evaluatePromotion: (profile: string) =>
    callMethod(`${API}.evaluate_promotion`, { profile }),
  computePension: (profile: string, calculation_date: string) =>
    callMethod(`${API}.compute_pension`, { profile, calculation_date }),
};
