# Frontend Integration Testing — Iraqi Government Payroll

Verification that the Next.js frontend correctly connects to the validated Frappe
backend (290 host tests + 18 smoke checks) and displays/uses real backend data. No
backend calculation logic was changed; no fake/demo data was added; no salary math
was duplicated in the frontend.

**Method:** the frontend is same-origin-proxied to Frappe (`next.config.mjs` rewrites
`/api/*` → the bench). I validated the integration **contract** end to end — built the
app, served it, logged in through the proxy, and exercised every API call the frontend
makes against the live backend, verifying each returns the exact shape the pages expect.

**Result:** all pages connect and render real data; every API contract matches; locked
payroll reads from the immutable snapshot; Arabic error messages flow correctly; lint +
build pass. **No frontend code bugs were found** (the frontend was hardened in prior
sessions). Genuine *feature gaps* (not bugs) are listed at the end.

---

## 1. Environment & API connection — PASS (one deploy note)
- Frontend `npm run build` ✓ (19 routes) and `npm run lint` ✓ (0 warnings).
- Backend reachable; **login works** (`/api/method/login` → 200, "Logged In").
- API base URL: **relative** — the browser calls the Next origin and `next.config.mjs`
  proxies `/api` to the Frappe site host, so there is **no CORS** and no host-routing
  404 (the fix from the earlier "Load failed" work).
- No CORS / 500 / ECONNRESET during the sweep.
- **Deploy note (not a frontend bug):** the bench **web server must be running**
  (`bench serve` / `bench start`). It was down at the start of this session, which makes
  every proxied call 500; starting it resolved everything. The container does not
  auto-start it.

## 2. Pages availability — PASS (with route-mapping notes)
| Requested page | Route | Status |
|---|---|---|
| Government Payroll dashboard | `/government-payroll` | ✅ real data |
| Employee Payroll Profiles | `/employees` (+ `/new`, `/[name]/edit`) | ✅ |
| Payroll Runs | `/payroll-runs` (+ `/[name]`) | ✅ |
| Promotions | `/promotions` | ✅ read-only list |
| Annual Increments | `/increments` | ✅ read-only list |
| Pension Calculations | `/pension` (Pension Register) | ✅ read-only |
| Reports | `/reports` | ✅ |
| Accounting Journal | `/accounting-journal` | ✅ |
| Calculation Snapshots | `/calculation-logs` | ✅ |
| (extra) Rule Sets / Salary Scale / Allowances | `/rule-sets` `/salary-scale` `/allowances` | ✅ |
| **Salary Calculation** | — | not a standalone page (salary preview lives in the employee form; payroll calculation runs from `/payroll-runs`) |
| **Bank Transfer** | — | not a standalone page; it is a report **type inside `/reports`** (`reports_api.bank_transfer`) |

## 3. Real data rendering — PASS
- Every list page fetches from `payrollApi.*` (Frappe); none use hardcoded/demo arrays
  (audited — 0 found). No Phase-1 placeholders remain.
- `getList` contract sweep (HTTP 200, real rows): Rule Set, Salary Scale, Allowance Rule,
  Annual Increment Request, Promotion Request, Pension Calculation, Payroll Period,
  Payroll Run, Salary Slip, **Payroll Calculation Snapshot**, Employee Profile — all 200.
- Columns match backend fields (typed in `shared/types`; build type-checks them).
- Arabic labels throughout; English numerals via the `.num` helper (LTR digits in RTL).
- Empty state shows only when the list is truly empty; loading/error states present on
  every page (the run-detail page uses inline loading/error around the governance fetch).

## 4. Forms & actions — PASS for implemented; gaps listed
- Create employee profile ✅ (`/employees/new` → `save_employee_profile`, RBAC-enforced).
- Edit employee profile ✅ (`/employees/[name]/edit`).
- Run salary calculation ✅ (create run on `/payroll-runs`, then `calculate` action).
- Create payroll run ✅ (`create_payroll_run`, duplicate guard).
- Submit for review / Approve / Lock / Unlock ✅ — the run-detail page renders buttons
  **strictly from the backend `allowed_actions`** and calls `run_governance_action`; the
  backend enforces state + role + lock immutability. Unlock appears only when the backend
  permits (Administrator).
- **Not implemented (feature gaps, see end):** create forms for Promotion Request, Annual
  Increment Request, and Pension Calculation. Those pages are read-only lists today; the
  records are created via Frappe Desk / the engine `apply_*` services.

## 5. Snapshot source of truth — PASS
- Verified live: a **Locked** run's `employee_register` returns rows from the immutable
  **Payroll Calculation Snapshot** (net 458,167) — the backend `reports_api._rows_for`
  selects the Snapshot for locked runs, Slip for active. Every export (CSV/Excel/PDF/
  bank/journal) goes through it.
- The frontend does **not** compute financial totals — `run_summary`, the registers,
  `bank_transfer` and `journal_export` all return finished numbers from the backend; the
  reports page only displays/exports them.
- (Display lookups, not calculations: the Employees list shows each employee's stored
  *scale* basic salary via a scale lookup, and the family editor previews dependent
  *counts* client-side; both mirror backend-stored values and the backend remains
  authoritative — no payroll math is duplicated.)

## 6. Error handling — PASS
Verified the exact Arabic messages the frontend surfaces (via `frappeClient.extractError`
reading `_server_messages`, and the salary-preview `message`):
- Missing/invalid grade+stage → «الدرجة «7» والمرحلة «99» غير موجودة في سلم الرواتب الفعّال…».
- Missing rule set → «مجموعة القواعد «NOPE» غير موجودة».
- Missing salary scale → handled by the same scale-check path (Arabic «لا يوجد سلم رواتب فعّال…»).
- Invalid employee profile (save) → Arabic `frappe.throw` surfaced on the form.
- Unauthorized action → backend `PermissionError` (DocType perms / governance role gate);
  the UI also hides the action via role helpers. (Permission messages are Frappe's
  standard text.)
- API failure → `frappeClient` extracts and shows the server message; pages render
  `ErrorBanner`.

## 7. UI/UX validation — PASS (code-level; visuals confirmed in prior shell work)
- RTL: `<html dir="rtl">` + every table is `text-right`; the shared `DataTable` renders
  `<th>`/`<td>` from one column array (no mis-aligned RTL columns).
- Cairo font: `next/font` Cairo applied app-wide (the slip PDF separately embeds Cairo).
- English numerals: `.num` helper (LTR, tabular) on all numbers.
- Responsive: grids use `sm:`/`lg:` breakpoints; tables are wrapped in `overflow-x-auto`
  for horizontal scroll on mobile.
- Loading / empty / error states present on every data page; buttons are labelled in
  Arabic with clear disabled/busy states.
- (Full pixel-level mobile regression requires a browser session; the app shell, RTL and
  Cairo rendering were visually confirmed in earlier sessions.)

## 8. Build validation — PASS
- `npm run lint` → no warnings/errors.
- `npm run build` → success, 19 routes compiled (static + dynamic).

---

## Broken pages
**None.** All routes build, load, and render real backend data.

## API contract mismatches
**None.** Every frontend call returns the expected shape:
`current_user{user,roles}`, `list_grades` (13), `salary_preview{valid,basic_salary,message}`,
`run_summary{employees,total_basic,total_earnings,total_deductions,total_net}`,
`employee_register/deductions_register{rows[]}`, `tax_register{rows,total_tax}`,
`bank_transfer{rows,count,incomplete_count,total_net}`, `pension_register{count,rows,totals}`,
`journal_export{balanced,…}`, `get_run_governance{workflow_state,allowed_actions,…}`, and all
`getList` DocTypes (HTTP 200 with full fields).

## UI-only bugs
**None found.**

## Fixes implemented
**None required** — no integration bug surfaced. (The frontend's proxy, method paths,
login gate, real-data wiring and RTL table alignment were fixed in earlier sessions and
verified here.) No backend logic was changed.

## Feature gaps (recommended next steps — NOT integration bugs)
1. **Create forms** for Promotion Request, Annual Increment Request, Pension Calculation
   (pages are read-only lists today; creation goes through Desk / `apply_*`). These would
   call new whitelisted create endpoints, mirroring the Employee form pattern.
2. A standalone **Salary Calculation** page (today: salary preview in the employee form +
   payroll runs). Optional.
3. A standalone **Bank Transfer** page (today: a report type inside `/reports`). Optional.
4. **Deploy:** ensure the bench web server (`bench serve`/gunicorn) auto-starts with the
   container so the frontend proxy always has an upstream.

## Final build result
`npm run lint` ✓ · `npm run build` ✓ (19 routes). Backend untouched: 290 host tests +
18 smoke checks remain green.
