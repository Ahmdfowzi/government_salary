# Iraqi Government Payroll — Production Build

Production-grade payroll system for Iraqi government employees.

- **Backend:** Frappe/ERPNext custom app `iraqi_government_payroll`, module **Government Payroll**.
- **Frontend:** Next.js (App Router), Arabic **RTL**, **Cairo** font, **English numerals**.
- **Hard rule:** every salary/tax/pension figure is computed in **Python on the backend**. The frontend only displays data and submits forms — it performs **no calculations**.

> The HTML prototype in `../iraqi-payroll-system/` is **UI/UX reference only** and is never imported as code.

## Layout

```
iraqi-government-payroll/
├── backend/iraqi_government_payroll/        Frappe app (bench app)
│   ├── pyproject.toml · MANIFEST.in · requirements.txt · license.txt
│   └── iraqi_government_payroll/
│       ├── hooks.py · modules.txt · patches.txt
│       ├── government_payroll/doctype/      34 DocTypes (incl. child tables)
│       ├── services/                        backend calc + governance services
│       │   ├── payroll_engine/ (+ governance.py)  tax/  pension/  allowance/
│       │   ├── promotion/  increment/  audit/
│       │   └── lifecycle/  historical/
│       ├── api/payroll_api.py               whitelisted REST (calc + governance)
│       ├── smoke/checks.py                  live bench smoke checks
│       └── fixtures/role.json               RBAC roles
└── frontend/                                Next.js + TS + Tailwind
    └── src/
        ├── app/government-payroll/...        routes (+ payroll-runs governance UI)
        └── shared/  components layouts forms tables services types
```

## Phase status

- **Phase 1 — structure & design.** ✅ DocTypes, RBAC roles, service skeletons and
  frontend routes. See `PHASE-1.md`.
- **Phase 2 — calculation engines.** ✅ Pure-Python active-salary / tax / pension /
  increment / promotion engines, official legal fixtures (one versioned
  `IRAQ-2015` rule set), Salary Slip + Payroll Run batch, and the test suite. See
  `PHASE-2-PLAN.md`.
- **Phase 3 — governance, lifecycle & operations (M1–M8).** ✅ Approval workflow,
  employee lifecycle, payroll locking + historical integrity, segregation-of-duties
  RBAC, an immutable governance audit log, a governance REST API, the Payroll Runs
  UI, and run creation. See **`PHASE-3.md`**.

**Current verification:** 164 backend tests pass (`python3 -m unittest`); the app is
validated on a **live Docker bench** (`docker/`) — `bench migrate` clean, 34
DocTypes, and four `bench execute` smoke checks (governance / locking / api /
create) green; `next build` + `next lint` pass. Engine boundaries and runtime
safety: `ENGINE-BOUNDARIES.md`. Install & bench checklist: `BENCH-READINESS.md`.
