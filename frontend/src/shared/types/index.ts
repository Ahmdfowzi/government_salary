// Shared TypeScript types mirroring the Frappe DocTypes.
// These describe data shapes ONLY — no calculation logic lives in the frontend.

export type ApprovalStatus =
  | "Draft"
  | "HR Review"
  | "Department Manager"
  | "Finance Review"
  | "Approved"
  | "Applied"
  | "Rejected";

export interface GovernmentSalaryLaw {
  name: string;
  law_code: string;
  law_name: string;
  law_year?: number;
  effective_from: string;
  effective_to?: string;
  status: "Draft" | "Active" | "Archived";
  source_reference?: string;
  notes?: string;
}

export interface GovernmentSalaryScaleDetail {
  grade_type: "Regular" | "Senior";
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
  salary_law: string;
  currency?: string;
  amount_unit?: "Actual" | "Thousand";
  is_active?: boolean;
  details: GovernmentSalaryScaleDetail[];
}

export interface GovernmentEmployeePayrollProfile {
  name: string;
  employee_number: string;
  employee_name: string;
  status: "Active" | "Suspended" | "Retired" | "Transferred";
  salary_law: string;
  qualification?: string;
  specialization?: string;
  current_grade: number;
  current_stage: number;
  basic_salary?: number;
  appointment_grade?: number;
  appointment_stage?: number;
  appointment_date?: string;
  marital_status?: string;
  eligible_children_count?: number;
  geographic_area?: string;
  risk_allowance_applicable?: boolean;
  protected_salary_difference?: number;
}

export interface QualificationAppointmentRule {
  name: string;
  salary_law: string;
  qualification_level: string;
  specialization?: string;
  starting_grade: number;
  starting_stage: number;
  certificate_allowance_percentage?: number;
  is_active?: boolean;
}

export interface AllowanceRule {
  name: string;
  component_code: string;
  component_name: string;
  allowance_type: "Earning" | "Deduction";
  context: "Active" | "Pension" | "Both";
  calculation_type: "Percentage" | "Fixed";
  basis?: "Basic" | "Pension Base" | "None";
  percentage?: number;
  fixed_amount?: number;
  capped_under_200?: "Yes" | "No" | "Undecided";
  confirmed?: boolean;
  is_active?: boolean;
}

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

export interface SalaryCalculationLog {
  name: string;
  employee_profile?: string;
  employee_name?: string;
  calculation_type?: string;
  calc_timestamp?: string;
  gross_amount?: number;
  total_deductions?: number;
  net_amount?: number;
}
