// Role-aware UI helpers (Phase 5 M2).
//
// These mirror the backend RBAC so the UI can HIDE or DISABLE actions a user may
// not perform. They are a UX convenience ONLY — the backend (governance
// allowed_actions, the accounting-export gate, DocType permissions) remains the
// single source of truth and re-checks every action. Never treat a hidden button
// as a security boundary.

export const ROLE = {
  SYSTEM_MANAGER: "System Manager",
  GOV_ADMIN: "Government Payroll Administrator",
  PAYROLL_ADMIN: "Payroll Administrator",
  PAYROLL_MANAGER: "Payroll Manager",
  PAYROLL_OFFICER: "Payroll Officer",
  HR_OFFICER: "HR Officer",
  HR_USER: "HR User",
  FINANCE_OFFICER: "Finance Officer",
  FINANCE_USER: "Finance User",
  AUDITOR: "Auditor",
  READ_ONLY: "Read Only User",
} as const;

const SUPERUSERS = [ROLE.SYSTEM_MANAGER, ROLE.GOV_ADMIN];

function hasAny(roles: string[], wanted: string[]): boolean {
  return roles.some((r) => wanted.includes(r));
}

export function isSuperuser(roles: string[]): boolean {
  return hasAny(roles, SUPERUSERS);
}

/** May the user write payroll/governance data (create runs, edit, etc.)? */
export function canManagePayroll(roles: string[]): boolean {
  return hasAny(roles, [...SUPERUSERS, ROLE.PAYROLL_ADMIN, ROLE.PAYROLL_MANAGER, ROLE.PAYROLL_OFFICER]);
}

/** May the user edit employee payroll profiles? (HR + payroll write roles) */
export function canEditProfiles(roles: string[]): boolean {
  return hasAny(roles, [
    ...SUPERUSERS, ROLE.PAYROLL_ADMIN, ROLE.PAYROLL_MANAGER, ROLE.PAYROLL_OFFICER,
    ROLE.HR_OFFICER, ROLE.HR_USER,
  ]);
}

/** May the user CREATE/SAVE a profile via the frontend form? Mirrors the backend
 *  DocType create/write perms exactly (Payroll Officer has read-only on profiles,
 *  so it is excluded here even though it can "manage payroll" elsewhere). The
 *  backend re-enforces this on every save — the gate here is UX only. */
export function canWriteProfiles(roles: string[]): boolean {
  return hasAny(roles, [
    ...SUPERUSERS, ROLE.PAYROLL_ADMIN, ROLE.PAYROLL_MANAGER, ROLE.HR_OFFICER, ROLE.HR_USER,
  ]);
}

/** May the user export reports (CSV/Excel/PDF)? Everyone except a pure Read Only User. */
export function canExportReports(roles: string[]): boolean {
  return hasAny(roles, [
    ...SUPERUSERS, ROLE.PAYROLL_ADMIN, ROLE.PAYROLL_MANAGER, ROLE.PAYROLL_OFFICER,
    ROLE.HR_OFFICER, ROLE.HR_USER, ROLE.FINANCE_OFFICER, ROLE.FINANCE_USER, ROLE.AUDITOR,
  ]);
}

/** May the user view/export the accounting journal? (mirrors the backend gate) */
export function canExportJournal(roles: string[]): boolean {
  return hasAny(roles, [
    ...SUPERUSERS, ROLE.PAYROLL_ADMIN, ROLE.PAYROLL_MANAGER,
    ROLE.FINANCE_OFFICER, ROLE.FINANCE_USER,
  ]);
}
