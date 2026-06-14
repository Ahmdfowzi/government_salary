# Frontend Feature Gaps — Implementation

Implements the gaps documented in `FRONTEND-INTEGRATION-TESTING.md`. No backend
calculation logic was changed — the new endpoints either create **draft** records
(the engine computes on approval) or run the **existing** pension service.

**Result:** 4 new routes + 3 new backend create endpoints, all using real Frappe
APIs/services. `npm run lint` ✓, `npm run build` ✓ (now 23 routes), backend tests
unchanged (290 host), and a new smoke check (`transaction_forms`) verifies the
create endpoints (now 19 smoke checks).

---

## 1. Transaction create forms (Promotion / Increment / Pension)

### Backend — 3 additive whitelisted endpoints (`api/payroll_api.py`)
- `create_increment_request(employee_profile, due_date?, remarks?)` — inserts a
  **Draft** Annual Increment Request. The new stage/salary are computed by the
  increment engine on the request's `on_submit` (apply), not here.
- `create_promotion_request(employee_profile, vacancy_available?, direct_manager_recommendation?, committee_decision?, remarks?)`
  — inserts a **Draft** Promotion Request. Target grade/stage/salary are computed by
  the promotion engine on approval, not here.
- `create_pension_calculation(employee_profile, service_years, average_36_months, last_functional_salary, last_full_salary?, extra_months?, other_deductions?, calculation_date?, remarks?)`
  — runs the **existing** `pension_service.compute_retirement_pension` (loaded via
  `repository.load_pension_rule_data`) and stores the result as a Pension Calculation
  record. **No new math.**

All three insert **without `ignore_permissions`**, so the DocType permissions enforce
RBAC (only payroll/HR roles can create); they raise an Arabic+English error on a bad
employee / missing rule set / missing pension rule.

### Frontend — 3 new routes
- `/government-payroll/increments/new` — employee + due date + remarks → draft.
- `/government-payroll/promotions/new` — employee + vacancy/manager/committee + remarks → draft.
- `/government-payroll/pension/new` — pension inputs → computes on the backend and shows
  the result (approved/certificate/COL/gross/tax/**net**/end-of-service) returned by the
  engine; no figures are computed in the browser.

Each form: real backend APIs; Arabic labels; RTL + Cairo + English numerals (`.num`);
loading/empty/error states; backend validation errors shown in Arabic; RBAC-gated
(`canManagePayroll`, backend re-enforces); no fake/demo data. The list pages
(`/increments`, `/promotions`, `/pension`) gained "+ إضافة …" buttons (write roles only).

## 2. Salary Calculation access
New `/government-payroll/salary-calculation` page (added to the sidebar as
**احتساب الراتب**): selects rule set + grade + stage and shows the **basic salary**
resolved by the backend (`salary_preview`, the same engine resolver payroll uses). It
clarifies that the full payroll (allowances/tax/pension/net) is computed in **Payroll
Runs**, and links there. No salary math in the frontend.

## 3. Bank Transfer access
Bank Transfer was already a **report type inside `/reports`** ("تحويل بنكي", calling
`reports_api.bank_transfer`). No separate page is needed; it reads the immutable Snapshot
for locked runs like the other reports. (Confirmed present and selectable.)

## 4. Deployment note / fix
The container's `frappe` service runs `sleep infinity`; the **Frappe web server is not
auto-started**, and the Next.js frontend proxy needs it (otherwise every `/api` call is
500 and login fails). `docker/README.md` §4 now documents this as **required** and gives
the exact start command (foreground and background):
```bash
docker compose -f docker/docker-compose.yml exec -d frappe \
  bash -lc "cd ~/frappe-bench && nohup bench serve --port 8000 >/tmp/benchserve.log 2>&1 &"
```
(The compose `command` was intentionally not changed, to avoid breaking the documented
one-time install flow; the README now makes the requirement explicit.)

## 5. Validation
- `npm run lint` → 0 warnings. `npm run build` → success (23 routes; the 4 new ones
  compiled: `increments/new`, `promotions/new`, `pension/new`, `salary-calculation`).
- API contract for the new forms verified two ways:
  - Smoke `transaction_forms` (new): creates an increment draft + a promotion draft +
    a pension calculation, asserts the pension is computed (net 819,167; EOS at 30y =
    last salary × 12) and the stored record matches; cleans up.
  - HTTP through the bench (the frontend path): `create_increment_request` → 200 with
    `{name, employee_profile, approval_status:"Draft", due_date}` (matches the frontend
    contract).
- Backend tests remain green: **290 host tests**. Smoke checks now **19** (added
  `transaction_forms`).

---

## New routes / components
| Route | Purpose |
|---|---|
| `/government-payroll/increments/new` | Create Annual Increment Request (draft) |
| `/government-payroll/promotions/new` | Create Promotion Request (draft) |
| `/government-payroll/pension/new` | Create Pension Calculation (engine-computed) |
| `/government-payroll/salary-calculation` | Salary preview (basic by grade/stage) |

New backend endpoints: `create_increment_request`, `create_promotion_request`,
`create_pension_calculation` (in `api/payroll_api.py`).

## Test / build results
- Frontend: lint ✓, build ✓ (23 routes).
- Backend: 290 host tests ✓; 19 smoke checks ✓ (incl. new `transaction_forms`).
- No backend calculation logic changed; no fake data added.
