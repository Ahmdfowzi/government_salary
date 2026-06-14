// Typed API surface for the Government Payroll module.
// Maps UI sections to Frappe DocTypes / whitelisted methods.
// Phase 2 M1: declares the data contract (read-only lists). Calculation
// endpoints remain backend-only placeholders — no math in the frontend.

import { getList, getDoc, callMethod, methodUrl } from "./frappeClient";
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
  RunSummaryReport,
  EmployeeRegisterReport,
  ComponentRegisterReport,
  TaxRegisterReport,
  PensionRegisterReport,
  BankTransferReport,
  JournalExport,
  CurrentUser,
  GovernmentGradeOption,
  SalaryPreview,
  SavedEmployeeProfile,
  PensionCalcResult,
} from "../types";

// Frappe dotted method paths. The app's Python package is `iraqi_government_payroll`
// (single — the inner package dir), so methods live at iraqi_government_payroll.api.*
// NOT iraqi_government_payroll.iraqi_government_payroll.api.* (that doubled path
// raises "No module named 'iraqi_government_payroll.iraqi_government_payroll'").
const API = "iraqi_government_payroll.api.payroll_api";
const REPORTS = "iraqi_government_payroll.api.reports_api";
const ACCT = "iraqi_government_payroll.api.accounting_api";
const SLIP = "iraqi_government_payroll.api.slip_api";

export const payrollApi = {
  // Versioning spine + rule members
  ruleSets: () => getList<GovernmentRuleSet>("Government Rule Set"),
  salaryScales: () => getList<GovernmentSalaryScale>("Government Salary Scale"),
  // Full scale doc incl. the `details` child table (grades/stages/basic salary) —
  // child rows are not returned by the list API, so we fetch the parent doc.
  salaryScale: (name: string) => getDoc<GovernmentSalaryScale>("Government Salary Scale", name),
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

  // Employee create/edit (Phase 5 M5). Master-data picker, live salary preview,
  // and create/update — the backend validates grade+stage and enforces RBAC.
  grades: () => callMethod<GovernmentGradeOption[]>(`${API}.list_grades`),
  salaryPreview: (rule_set: string, grade: string, stage: number | string) =>
    callMethod<SalaryPreview>(`${API}.salary_preview`, { rule_set, grade, stage }),
  saveEmployeeProfile: (
    payload: Partial<GovernmentEmployeePayrollProfile>,
    name?: string,
  ) =>
    callMethod<SavedEmployeeProfile>(`${API}.save_employee_profile`, {
      payload: JSON.stringify(payload),
      name,
    }),

  // Transactions
  increments: () => getList<AnnualIncrementRequest>("Annual Increment Request"),
  promotions: () => getList<PromotionRequest>("Promotion Request"),
  pensions: () => getList<PensionCalculation>("Pension Calculation"),

  // Transaction create forms (Phase 5 M8). Increment/Promotion are created as
  // DRAFTS (the engine computes grade/stage/salary on approval); the pension
  // calculation runs the existing pension service and stores the result. The
  // backend enforces permissions and all computation.
  createIncrementRequest: (employee_profile: string, due_date?: string, remarks?: string) =>
    callMethod<{ name: string; approval_status: string }>(
      `${API}.create_increment_request`, { employee_profile, due_date, remarks }),
  createPromotionRequest: (
    employee_profile: string,
    opts: { vacancy_available?: number; direct_manager_recommendation?: number; committee_decision?: string; remarks?: string },
  ) =>
    callMethod<{ name: string; approval_status: string }>(
      `${API}.create_promotion_request`, { employee_profile, ...opts }),
  createPensionCalculation: (payload: {
    employee_profile: string; service_years: number; average_36_months: number;
    last_functional_salary: number; last_full_salary?: number; extra_months?: number;
    other_deductions?: number; calculation_date?: string; remarks?: string;
  }) => callMethod<PensionCalcResult>(`${API}.create_pension_calculation`, payload),

  // Operational
  payrollPeriods: () => getList<PayrollPeriod>("Payroll Period"),
  payrollRuns: () => getList<PayrollRun>("Payroll Run"),
  salarySlips: () => getList<SalarySlip>("Salary Slip"),

  // Session (role-aware UI; backend enforces all restrictions)
  currentUser: () => callMethod<CurrentUser>(`${API}.current_user`),
  // Auth: establish / clear a Frappe session on the frontend origin (via the
  // same-origin proxy) so credentialed API calls are authenticated. The frontend
  // has no other way to obtain a session — Frappe enforces all permissions.
  login: (usr: string, pwd: string) => callMethod<{ message?: string }>(`login`, { usr, pwd }),
  logout: () => callMethod(`logout`),

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

  // Read-only payroll reports (Phase 4 M10). Backend chooses Salary Slip (active
  // run) vs immutable Snapshot (locked run); the UI only displays/exports.
  reportRunSummary: (run: string) =>
    callMethod<RunSummaryReport>(`${REPORTS}.run_summary`, { run }),
  reportEmployeeRegister: (run: string) =>
    callMethod<EmployeeRegisterReport>(`${REPORTS}.employee_register`, { run }),
  reportAllowances: (run: string) =>
    callMethod<ComponentRegisterReport>(`${REPORTS}.allowances_register`, { run }),
  reportDeductions: (run: string) =>
    callMethod<ComponentRegisterReport>(`${REPORTS}.deductions_register`, { run }),
  reportTax: (run: string) =>
    callMethod<TaxRegisterReport>(`${REPORTS}.tax_register`, { run }),
  reportPensionRegister: (from_date?: string, to_date?: string, status?: string) =>
    callMethod<PensionRegisterReport>(`${REPORTS}.pension_register`, {
      from_date,
      to_date,
      status,
    }),
  reportBankTransfer: (run: string) =>
    callMethod<BankTransferReport>(`${REPORTS}.bank_transfer`, { run }),
  // URL for a report file download (xlsx or pdf) — the browser fetches it directly.
  exportReportUrl: (
    report: string,
    params: { run?: string; from_date?: string; to_date?: string; status?: string },
    fmt: "xlsx" | "pdf" = "xlsx",
  ) => methodUrl(`${REPORTS}.export_report`, { report, fmt, ...params }),

  // Government Payroll Slip (مفردات راتب): generate from the post-calc snapshot
  // (POST/write), then fetch the printable PDF read-only by name (GET).
  generateLatestSlip: (employee: string) =>
    callMethod<{ name: string; net_pay: number; source: string }>(
      `${SLIP}.generate_latest_slip`,
      { employee },
    ),
  slipPdfUrl: (name: string) => methodUrl(`${SLIP}.render_payroll_slip_pdf`, { name }),

  // Accounting journal (proposal only — no GL posting).
  journalExport: (run: string) =>
    callMethod<JournalExport>(`${ACCT}.journal_export`, { run }),
  journalExportUrl: (run: string) =>
    methodUrl(`${ACCT}.export_journal`, { run, fmt: "xlsx" }),

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
