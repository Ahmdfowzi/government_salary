// Shared TypeScript types mirroring the Frappe DocTypes.
// These describe data shapes ONLY — no calculation logic lives in the frontend.

export type RuleStatus = "Draft" | "Active" | "Archived";

export type ApprovalStatus =
  | "Draft"
  | "HR Review"
  | "Department Manager"
  | "Finance Review"
  | "Approved"
  | "Applied"
  | "Rejected";

// ---- Versioning spine ----

export interface GovernmentRuleSet {
  name: string;
  rule_set_code: string;
  rule_set_name: string;
  year?: number;
  effective_from: string;
  effective_to?: string;
  status: RuleStatus;
  source_reference?: string;
  notes?: string;
}

export interface RuleSetParameter {
  parameter_key: string;
  parameter_label?: string;
  value_type?: "Percentage" | "Currency" | "Int" | "Boolean" | "Select" | "Text";
  value?: string;
  confirmed?: boolean;
  notes?: string;
}

// ---- Organization ----

export type EntityType =
  | "Ministry"
  | "Authority"
  | "Governorate"
  | "Directorate"
  | "Department"
  | "Division"
  | "Unit";

export interface GovernmentEntity {
  name: string;
  entity_code: string;
  entity_name_ar: string;
  entity_name_en?: string;
  entity_type: EntityType;
  parent_government_entity?: string;
  is_group?: boolean;
  is_active?: boolean;
}

export interface GovernmentPosition {
  name: string;
  position_code: string;
  position_name_ar: string;
  position_name_en?: string;
  government_entity?: string;
  grade_band?: string;
  position_allowance_category?: string;
  risk_category?: string;
  is_managerial?: boolean;
  head_count?: number;
  is_active?: boolean;
}

// ---- Salary scale ----

export interface GovernmentSalaryScaleDetail {
  grade_type: "Regular" | "Senior";
  grade_code?: string;
  grade: number;
  stage: number;
  basic_salary: number;
  annual_increment?: number;
  promotion_years?: number;
  senior_title?: string;
}

export interface GovernmentSalaryScale {
  name: string;
  scale_name: string;
  rule_set: string;
  currency?: string;
  amount_unit?: "Actual" | "Thousand";
  is_active?: boolean;
  details: GovernmentSalaryScaleDetail[];
}

// ---- Employee ----

export interface GovernmentEmployeePayrollProfile {
  name: string;
  employee_number: string;
  employee_name: string;
  status: "Active" | "Suspended" | "Retired" | "Transferred";
  rule_set: string;
  qualification?: string;
  specialization?: string;
  government_entity?: string;
  government_position?: string;
  employment_type?: "Permanent" | "Contract" | "Daily Wage" | "Temporary";
  bank_account?: string;
  grade_code?: string;
  current_grade: number;
  current_stage: number;
  basic_salary?: number;
  appointment_grade?: number;
  appointment_stage?: number;
  appointment_date?: string;
  current_stage_date?: string;
  current_grade_date?: string;
  retirement_service_start_date?: string;
  marital_status?: string;
  eligible_children_count?: number;
  geographic_area?: string;
  risk_allowance_applicable?: boolean;
  protected_salary_difference?: number;
}

export interface EmployeeMonthlySalary {
  name: string;
  employee_profile: string;
  employee_name?: string;
  salary_month: string;
  fiscal_year?: number;
  functional_salary?: number;
}

// ---- Rule members ----

export interface QualificationAppointmentRule {
  name: string;
  rule_set: string;
  qualification_level: string;
  specialization?: string;
  starting_grade: number;
  starting_stage: number;
  certificate_allowance_percentage?: number;
  status?: RuleStatus;
  is_active?: boolean;
}

export interface AllowanceRule {
  name: string;
  component_code: string;
  component_name: string;
  rule_set: string;
  status?: RuleStatus;
  allowance_type: "Earning" | "Deduction";
  context: "Active" | "Pension" | "Both";
  match_key?: "Qualification" | "Position" | "Job Category" | "Global";
  match_value?: string;
  calculation_type: "Percentage" | "Fixed";
  basis?: "Basic" | "Pension Base" | "None";
  percentage?: number;
  fixed_amount?: number;
  capped_under_200?: "Yes" | "No" | "Undecided";
  confirmed?: boolean;
  is_active?: boolean;
}

export interface IncomeTaxBracket {
  name: string;
  rule_set: string;
  status?: RuleStatus;
  seq: number;
  from_amount?: number;
  to_amount?: number;
  rate?: number;
  period?: "Annual" | "Monthly";
}

export interface TaxAllowanceRule {
  name: string;
  rule_set: string;
  status?: RuleStatus;
  taxpayer_status: "Single" | "Married" | "Per Child" | "Life Insurance" | "Other";
  basis?: "Fixed" | "Per Dependent";
  annual_amount?: number;
  max_annual_cap?: number;
  confirmed?: boolean;
}

export interface PensionRule {
  name: string;
  rule_set: string;
  status?: RuleStatus;
  law_article?: string;
  accrual_rate?: number;
  averaging_months?: number;
  cap_pct_of_last_salary?: number;
  eos_min_service_years?: number;
  default_minimum_pension?: number;
  cost_of_living_method?: string;
  cost_of_living_value?: number;
}

export interface PromotionGradeDuration {
  from_grade: string;
  to_grade: string;
  years: number;
}

export interface PromotionRule {
  name: string;
  rule_set: string;
  status?: RuleStatus;
  new_stage_policy?: string;
  durations?: PromotionGradeDuration[];
  requires_vacancy?: boolean;
  requires_manager_recommendation?: boolean;
  requires_committee?: boolean;
  requires_higher_approval?: boolean;
}

export interface AnnualIncrementRule {
  name: string;
  rule_set: string;
  status?: RuleStatus;
  eligibility_months?: number;
  increment_basis?: string;
  description?: string;
}

export interface GeographicArea {
  name: string;
  rule_set: string;
  status?: RuleStatus;
  area_code: string;
  area_name_ar: string;
  area_name_en?: string;
  fixed_amount?: number;
  capped_under_200?: "Yes" | "No" | "Undecided";
  confirmed?: boolean;
}

// ---- Transactions ----

export interface AnnualIncrementRequest {
  name: string;
  employee_profile: string;
  employee_name?: string;
  current_grade?: number;
  current_stage?: number;
  new_stage?: number;
  current_salary?: number;
  new_salary?: number;
  increment_amount?: number;
  due_date?: string;
  approval_status: ApprovalStatus;
}

export interface PromotionRequest {
  name: string;
  employee_profile: string;
  employee_name?: string;
  from_grade?: number;
  to_grade?: number;
  proposed_stage?: number;
  old_salary?: number;
  new_salary?: number;
  years_in_grade?: number;
  approval_status: string;
}

export interface PensionCalculation {
  name: string;
  employee_profile: string;
  employee_name?: string;
  calculation_date?: string;
  average_36_months?: number;
  approved_pension?: number;
  gross_pension?: number;
  net_pension?: number;
  status: "Draft" | "Calculated" | "Approved";
}

// ---- Operational ----

export interface PayrollPeriod {
  name: string;
  period_name?: string;
  year: number;
  month: number;
  start_date?: string;
  end_date?: string;
  status: "Open" | "Calculating" | "Review" | "Approved" | "Locked";
}

export type WorkflowState =
  | "Draft"
  | "Calculated"
  | "Under Review"
  | "Approved"
  | "Submitted"
  | "Locked"
  | "Cancelled";

export interface PayrollRun {
  name: string;
  payroll_period: string;
  rule_set?: string;
  scope?: "Employee" | "Government Entity" | "All";
  scope_reference?: string;
  workflow_state?: WorkflowState;
  run_status?: "Draft" | "Queued" | "Completed" | "Failed";
  run_date?: string;
}

// One immutable governance transition (mirrors Payroll Run Governance Event).
export interface GovernanceEvent {
  action: string;
  from_state: string;
  to_state: string;
  actor: string;
  event_timestamp: string;
}

// Read model returned by api.payroll_api.get_run_governance / run_governance_action.
// `allowed_actions` is the AUTHORITATIVE list of actions the caller may take now —
// computed entirely on the backend. The UI renders buttons from it and never
// re-derives transitions or permissions.
export interface RunGovernance {
  name: string;
  workflow_state: WorkflowState;
  run_status?: string;
  error_count?: number;
  allowed_actions: string[];
  audit: Record<string, string | null>;
  events: GovernanceEvent[];
}

// Phase 4 M10 — read-only payroll report models (api.reports_api).
export interface RunSummaryReport {
  run: string;
  employees: number;
  total_basic: number;
  total_earnings: number;
  total_deductions: number;
  total_net: number;
}

export interface EmployeeRegisterRow {
  employee_profile: string;
  employee_name: string;
  grade_code?: string;
  stage?: number;
  basic: number;
  allowances: number;
  deductions: number;
  net: number;
}
export interface EmployeeRegisterReport {
  run: string;
  rows: EmployeeRegisterRow[];
  totals: { basic: number; allowances: number; deductions: number; net: number };
}

export interface ComponentRegisterRow {
  employee_profile: string;
  employee_name: string;
  component_code: string;
  component_name?: string;
  amount: number;
  basis_amount?: number;
  rate?: number | null;
}
export interface ComponentRegisterReport {
  run: string;
  rows: ComponentRegisterRow[];
  totals_by_component: Record<string, number>;
  grand_total: number;
}

export interface TaxRegisterRow {
  employee_profile: string;
  employee_name: string;
  taxable: number;
  tax: number;
}
export interface TaxRegisterReport {
  run: string;
  rows: TaxRegisterRow[];
  total_tax: number;
}

// Phase 4 M11 — Retirement Pension Register (read-only, from Pension Calculation
// / Retirement Pension Snapshot).
export interface PensionRegisterRow {
  employee_profile: string;
  employee_name: string;
  qualification: string;
  service_years: number;
  average_36_months: number;
  approved_pension: number;
  certificate_allowance: number;
  cost_of_living: number;
  gross_pension: number;
  monthly_tax: number;
  other_deductions: number;
  net_pension: number;
  end_of_service_bonus: number;
  status: string;
  calculation_date: string;
}
export interface PensionRegisterReport {
  from_date: string | null;
  to_date: string | null;
  status: string | null;
  count: number;
  rows: PensionRegisterRow[];
  totals: Record<string, number>;
}

// Phase 4 M12 — Bank Transfer Export (read-only). Net comes from Salary Slip /
// Snapshot; bank details from the profile. Incomplete rows are flagged, not skipped.
export interface BankTransferRow {
  employee_profile: string;
  employee_name: string;
  iban: string;
  bank_name: string;
  bank_account: string;
  national_id: string;
  net: number;
  bank_complete: boolean;
  missing: string[];
}
export interface BankTransferReport {
  run: string;
  rows: BankTransferRow[];
  count: number;
  incomplete_count: number;
  total_net: number;
}

// Phase 4 M15 — Accounting journal export (proposal only; no GL posting).
export interface JournalRow {
  account: string;
  description: string;
  debit: number;
  credit: number;
}
export interface JournalExport {
  run: string;
  rows: JournalRow[];
  total_debit: number;
  total_credit: number;
  balanced: boolean;
  summary: Record<string, number>;
}

// Phase 5 M2 — logged-in user + roles (role-aware UI only; backend enforces).
export interface CurrentUser {
  user: string;
  roles: string[];
}

export interface SalarySlipLine {
  component_code?: string;
  component_name?: string;
  line_type?: "Earning" | "Deduction";
  amount?: number;
  basis_amount?: number;
  rate?: number;
  cap_applied?: boolean;
  source_rule?: string;
  reason_text?: string;
}

export interface SalarySlip {
  name: string;
  employee_profile: string;
  employee_name?: string;
  payroll_period?: string;
  payroll_run?: string;
  rule_set?: string;
  grade?: number;
  grade_code?: string;
  stage?: number;
  basic_salary?: number;
  total_capped_allowances?: number;
  total_non_capped_allowances?: number;
  total_earnings?: number;
  total_deductions?: number;
  net_salary?: number;
  status?: "Draft" | "Submitted" | "Locked";
  lines?: SalarySlipLine[];
}

// ---- Audit / reproducibility ----

export interface PayrollCalculationSnapshot {
  name: string;
  employee_profile?: string;
  employee_name?: string;
  calculation_type?: string;
  calc_timestamp?: string;
  period_date?: string;
  rule_set?: string;
  rule_set_version?: string;
  engine_version?: string;
  salary_slip?: string;
  payroll_period?: string;
  gross_amount?: number;
  total_deductions?: number;
  net_amount?: number;
}
