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
│       ├── government_payroll/doctype/      9 DocTypes (+2 child tables)
│       ├── services/                        backend calculation services
│       │   ├── payroll_engine/  tax/  pension/  allowance/
│       │   └── promotion/  increment/  audit/
│       ├── api/payroll_api.py               whitelisted REST endpoints
│       └── fixtures/role.json               RBAC roles
└── frontend/                                Next.js + TS + Tailwind
    └── src/
        ├── app/government-payroll/...        9 routes
        └── shared/  components layouts forms tables services types
```

## Phase status

- **Phase 1 (this build): structure & design only.** DocTypes, RBAC, service
  placeholders and frontend routes exist. **No calculation logic, no dashboards,
  no full UI, no hardcoded legal numbers.**
- **Phase 2:** implement the Python engines, load official legal figures as
  fixtures, build the data-entry/list UI, and add tests.

See `PHASE-1.md` for the full file manifest and the Phase 2 backlog.
