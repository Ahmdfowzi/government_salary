# Phase 1 — Deliverable Manifest

Structure & design only. No calculation logic, no dashboards, no full UI, no
hardcoded legal numbers. 91 files created.

## A. DocTypes (design only) — `backend/.../government_payroll/doctype/`

Each DocType folder has: `{name}.json` (fields, types, required, links,
permissions), `{name}.py` (purpose + relationships + documented validation
rules as Phase-2 stubs), and `__init__.py`.

| DocType | Type | Purpose |
|---|---|---|
| Government Salary Law | Master | Versioned salary law/scale header (SCALE_2015…), effective dates, status. |
| Government Salary Scale | Master + child | Grade/stage basic-salary matrix for a law. |
| Government Salary Scale Detail | Child table | One (grade, stage, basic, increment) row. *(supporting)* |
| Government Employee Payroll Profile | Master | Per-employee payroll state: law, grade/stage, qualification, family, dates. |
| Qualification Appointment Rule | Master | Certificate → starting grade/stage + certificate allowance %. |
| Allowance Rule | Master | Catalog of components (earning/deduction), basis, 200%-cap flag, validity. |
| Annual Increment Request | Transaction (submittable) | Approve & apply one-stage annual increment. |
| Promotion Request | Transaction (submittable) | Approve & apply a grade promotion with salary protection. |
| Pension Calculation | Transaction (submittable) | Article-21 pension: 36-mo avg, cap, allowance, COL, tax, net, EOS. |
| Salary Calculation Log | Audit (immutable) | Write-once audit trail with totals + JSON snapshots. |
| Salary Calculation Log Line | Child table | Per-component explained breakdown. *(supporting)* |

**Permissions model (roles):** Payroll Administrator, Payroll Manager, Payroll
Officer, HR User, Finance User, Auditor (+ System Manager). Masters: admin/manager
write, others read. Transactions: HR/Officer create, Manager/Finance submit.
Audit log: read-only for all (no write/delete) — created by backend only.

## B. Backend services (placeholders) — `backend/.../services/`

`payroll_engine/engine.py`, `tax/tax_service.py`, `pension/pension_service.py`,
`allowance/allowance_service.py`, `promotion/promotion_service.py`,
`increment/increment_service.py`, `audit/audit_service.py` — documented function
signatures that raise `NotImplementedError` (Phase 2).

`api/payroll_api.py` — whitelisted REST endpoints the frontend calls (stubs).

## C. App scaffolding

`hooks.py` (app metadata + role fixtures), `modules.txt` (`Government Payroll`),
`patches.txt`, `pyproject.toml`, `MANIFEST.in`, `requirements.txt`,
`license.txt`, `fixtures/role.json`.

## D. Frontend — `frontend/`

- `src/app/layout.tsx` — RTL (`dir="rtl" lang="ar"`) + Cairo font via next/font.
- `src/app/globals.css` — RTL base + `.num` utility forcing English numerals.
- `src/app/government-payroll/layout.tsx` + 9 routes (home, salary-laws,
  salary-scale, employees, allowances, increments, promotions, pension,
  calculation-logs) — placeholder pages.
- `src/shared/`: `components/` (PageHeader, EmptyState), `layouts/` (Sidebar +
  nav), `forms/` (FormShell), `tables/` (DataTable), `services/` (frappeClient,
  api), `types/` (DocType interfaces).

## What is READY
- Installable Frappe app skeleton (`bench get-app` / `bench install-app`-ready layout).
- All 9 DocTypes + 2 child tables: fields, types, required, relationships, permissions — JSON validated, controllers compile.
- RBAC roles fixture; backend service + API stubs; Next.js RTL/Cairo shell with all 9 routes and shared building blocks.

## PENDING for Phase 2
1. Implement Python engines (active salary, 200% cap, tax brackets, pension, increment, promotion) + audit log writing.
2. Enforce documented validation rules (V1…) in controllers.
3. Load official legal figures as fixtures (2015/2008 scales, tax brackets/allowances, pension rate, family/geographic/risk amounts) — data, not code.
4. Build list/detail/data-entry UI over the Frappe REST API; wire calculation endpoints.
5. Workflow (Workflow + Workflow State) for increment/promotion approval chains.
6. Tests: Python unit tests for engines, integration tests for permissions/validations/audit writes.
