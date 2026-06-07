# Project Status — Iraqi Government Payroll

> Handoff snapshot. Backend = Frappe v15 app `iraqi_government_payroll` (module
> **Government Payroll**); Frontend = Next.js (App Router, Arabic RTL, Cairo).
> Validated on a live Docker bench (`docker/`), Python 3.12.

## Snapshot

| Item | Value |
|---|---|
| Current phase / milestone | **Phase 4 — M13 (complete)** |
| Last completed milestone | **M13 — Excel export for payroll reports** |
| Current HEAD commit | **`029d259`** |
| Total DocTypes (Government Payroll module) | **34** |
| Backend tests passing | **188** (`python3 -m unittest`, no bench) |
| Smoke checks passing | **8 / 8** (live bench, `bench execute`) |
| Frontend build (`npm run build`) | **✓ passing** |
| Frontend lint (`npm run lint`) | **✓ passing** (no warnings/errors) |
| Working tree | clean |

Smoke checks (all exit 0): `governance` · `locking` · `api` · `create` ·
`reports` · `pension_report` · `bank_transfer` · `excel_export`
(run via `bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.<name>`).

---

## Completed Milestones

### Phase 1 — Structure & design
- **Purpose:** scaffold the app — DocTypes, RBAC roles, service skeletons, frontend routes. No calculation logic.
- **Key files:** `government_payroll/doctype/*`, `fixtures/role.json`, `PHASE-1.md`, frontend route placeholders.
- **Verification:** structural (JSON schema / imports).
- **Commit:** `bca9f40`.

### Phase 2 — Calculation engines (M1–M9.x)
- **Purpose:** pure-Python engines (active salary, tax, pension, increment, promotion), versioned `IRAQ-2015` rule set + legal fixtures, Salary Slip + Payroll Run batch, Docker bench. Anchors reproduce exactly (e.g. Bachelor g7s1 basic 296000 / gross 429200 / net 371487; pension net 1,049,744).
- **Key files:** `services/payroll_engine/`, `services/tax/`, `services/pension/`, `services/allowance/`, `services/increment/`, `services/promotion/`, `services/audit/`, `fixtures/*.json`, `docker/`, `PHASE-2-PLAN.md`, `ENGINE-BOUNDARIES.md`, `BENCH-READINESS.md`.
- **Verification:** pure unit/integration tests; later validated live on the Docker bench.
- **Commits:** `93cb9ba` (M1) … `8a3384a` (M9.5). Engine boundaries: see `ENGINE-BOUNDARIES.md`.

### Phase 3 — Governance, lifecycle & operations (see `PHASE-3.md`)

| M | Purpose | Key files | Verification | Commit |
|---|---------|-----------|-------------|--------|
| **M1** | Payroll Run governance state machine (Draft→Calculated→Under Review→Approved→Submitted→Locked, +Cancelled) | `services/payroll_engine/governance.py`, `doctype/payroll_run/payroll_run.py` | unit tests | `2284bec` |
| **M2** | Employee lifecycle (appoint/transfer/leave/return/retire/terminate); immutable events | `services/lifecycle/`, lifecycle DocTypes | unit tests | `a899113` |
| **M3** | Payroll locking + historical integrity (reconstruct from immutable snapshots) | `services/historical/`, `governance.py` (Locked) | unit tests | `c4bd3ca` |
| **M3.1** | Block deletion of Submitted/Locked runs | `payroll_run.py` (`on_trash`) | unit tests | `1477f53` |
| **M4** | Segregation-of-duties RBAC (`REQUIRED_ROLES`, `ensure_role_allowed`) | `governance.py`, `payroll_run.py` | unit tests | `75134c6` |
| **M5** | Immutable governance audit log (one event per transition) | `doctype/payroll_run_governance_event/`, `governance.py`, `payroll_run.py` | unit tests | `007c24a` |
| **M5.1** | Smoke harness hardened (`bench execute`, fail-hard, no false PASSED) | `smoke/checks.py`, `docker/smoke-*.py` | live bench | `218798e` |
| **M5.2** | Pin bench Python to 3.12.12 | `docker/install-app.sh` | live migrate | `ff18c94` |
| **M5.3** | Fix `is_locked()` shadowing Frappe's `Document.is_locked` → `is_run_locked()` | `payroll_run.py`, `test_locking.py` | unit + live | `14d2fdd` |
| **M6** | Governance REST API (`run_governance_action`, `get_run_governance`, `available_actions`) | `api/payroll_api.py`, `governance.py` | +14 tests, live | `6fba1ef` |
| **M7** | Payroll Runs governance UI (list + detail; buttons from `allowed_actions`; audit + event timeline) | `frontend .../payroll-runs/*`, `api.ts`, `frappeClient.ts` | build/lint, live api smoke | `d537937` |
| **M8** | Payroll Run creation (thin validated endpoint + form; duplicate guard) | `api/payroll_api.py`, `frontend .../payroll-runs/page.tsx` | +9 tests, live | `1273793` |
| **M9** | Docs sweep — `PHASE-3.md`, README phase status, docker/README, ENGINE-BOUNDARIES, BENCH-READINESS | the 5 docs | facts re-verified | `327762d` |

### Phase 4 — Reports & export

| M | Purpose | Key files | Verification | Commit |
|---|---------|-----------|-------------|--------|
| **M10** | 5 read-only payroll reports + CSV (Run Summary, Employee/Allowances/Deductions/Tax registers) | `services/reports/report_service.py`, `api/reports_api.py`, `frontend .../reports/page.tsx`, `shared/services/csv.ts` | +9 tests, live `reports` smoke | `0911017` |
| **M11** | Retirement Pension Register (read-only; from Pension Calculation / Retirement Pension Snapshot) | `report_service.pension_register`, `reports_api.pension_register` | +5 tests, live `pension_report` smoke | `6b6503e` |
| **M12** | Bank Transfer Export + 3 optional profile fields (`iban`, `bank_name`, `national_id`) | `reports_api.bank_transfer`, profile DocType JSON (migrated) | +5 tests, live `bank_transfer` smoke, `bench migrate` | `3acd940` |
| **M13** | Excel (.xlsx) export for all 7 reports (openpyxl) | `services/reports/report_columns.py`, `services/reports/xlsx_export.py`, `reports_api.export_report` | +5 tests, live `excel_export` smoke | `029d259` |

---

## Current System State

- **Governance workflow:** ✅ Complete. Server-enforced state machine + RBAC + immutable audit log; REST API + UI; run creation. Every transition checks role (M4) and writes one immutable event (M5); a failed audit insert aborts the transition.
- **Reports:** ✅ 5 payroll registers (Run Summary, Employee, Allowances, Deductions, Tax) — read-only, sourced from Salary Slip (active) / Snapshot (locked); totals reconcile to the slip (no recomputation). CSV + Excel export.
- **Pension register:** ✅ Retirement Pension Register (15 columns), filtered by `from_date`/`to_date`/`status`; reads stored Pension Calculation values, immutable Retirement Pension snapshot for finalized records. No retirement calculation in the report.
- **Bank transfer:** ✅ Per-employee net (Slip/Snapshot) + profile bank details; every row included; incomplete rows **flagged not skipped**. CSV + Excel.
- **Excel export:** ✅ All 7 reports via backend openpyxl (no new dependency, no SheetJS). RTL sheet, bold header/totals; booleans → نعم/لا, lists joined; downloaded via a browser GET to `export_report`.

---

## Deferred Milestones

- **M14 — PDF Export.** Not started. `wkhtmltopdf` is present in the bench; the real work is RTL/Arabic-font HTML/Jinja templates. **Reuses `services/reports/report_columns.py`** (built in M13). Weaker automated testability (binary PDF).
- **Accounting Journal Export.** Not started. The only remaining report that is **not** a pure read — needs a new component→GL-account **mapping config** (DocType/fixture), balancing (debits = credits), and accounting decisions. Largest scope; do last.

---

## Known Technical Notes

- **Python 3.12 pin (required).** Frappe v15 supports Python 3.10–3.12 only. The `frappe/bench` image defaults to **3.14**, which breaks the document-save `file_lock` path. `docker/install-app.sh` pins the bench virtualenv to **3.12.12** and self-heals an existing env (site/DB preserved). Do **not** run on 3.13/3.14.
- **`is_locked` shadowing (resolved in M5.3).** A controller method named `is_locked()` shadowed Frappe's `Document.is_locked` **property**, which `check_if_locked()` evaluates as a boolean on every save → a bound method is always truthy → `lock_age().stat()` on a non-existent lock → `FileNotFoundError`, breaking every save on a real bench. **Fix:** renamed to `is_run_locked()`; a regression test asserts the class does not define `is_locked`. **Rule:** never name a controller method the same as a Frappe `Document` property/method (`is_locked`, `is_new`, …); fake-frappe unit tests won't catch it — only a live bench will.
- **Snapshot vs Salary Slip source selection.** Reports read the **live Salary Slip** for an **active** run and the **immutable Payroll Calculation Snapshot** for a **Locked** run (`reports_api._rows_for` → `governance.is_locked`). For the pension register, **finalized (status Approved)** records read monetary figures from the immutable **Retirement Pension snapshot** (identity/metadata stay from the live record; `service_years` recovered from the snapshot's stored `service_months`). Net salary is always read, never recomputed.
- **Bank transfer completeness.** A row is `bank_complete` only if **(iban OR bank_account) AND net > 0**; otherwise it is included with `bank_complete=false` and a `missing` reasons list — never silently skipped. In Excel, `bank_complete` renders نعم/لا and `missing` joins with "، ".
- **openpyxl on the host for tests.** openpyxl is a transitive Frappe dependency (present in the bench, **not** added to `requirements.txt`). The host test machine needs it to reopen workbooks in `test_reports.py`: `pip install openpyxl`.

---

## Resume Instructions

1. **Confirm a clean baseline.**
   - `git -C "<repo>" log --oneline -1` → expect `029d259` (Phase 4 M13); working tree clean.
   - Backend tests: `cd backend/iraqi_government_payroll/iraqi_government_payroll/tests && python3 -m unittest discover -p 'test_*.py'` → **188 OK** (install openpyxl on the host first if absent).
   - Frontend: `cd frontend && npm run build && npm run lint` → both pass.
2. **Bring up the live bench if needed.** `docker compose -f docker/docker-compose.yml up -d`, then `docker compose ... exec frappe bash /mnt/scripts/install-app.sh` (pins Python 3.12, migrates, prints fixture counts: 143/16/4/9/6, 34 DocTypes).
3. **Re-run the 8 smoke checks** (all should exit 0):
   `for c in governance locking api create reports pension_report bank_transfer excel_export; do docker compose -f docker/docker-compose.yml exec frappe bash -lc "cd ~/frappe-bench && bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.$c"; done`
4. **Next milestone — M14 (PDF Export).** Recommended next. Scope-first (the project convention): propose scope, get approval, then implement.
   - Reuse `services/reports/report_columns.py` (column specs) — do **not** duplicate report aggregation.
   - Add a `pdf_export` serializer + extend `export_report` with `fmt="pdf"`; keep reports read-only; reuse the Slip/Snapshot source selection.
   - Decide: Frappe `get_pdf` (wkhtmltopdf, already present) with an RTL Arabic HTML/Jinja template. **Verify Arabic fonts render in the container** before committing to it (the main risk).
   - Add a "تنزيل PDF" button mirroring the Excel button.
   - Verify: reopen/inspect output where possible (PDF magic bytes + `pdftotext` for a known value), full backend suite, a `pdf_export` smoke check, `npm run build`/`lint`.
5. **After M14:** Accounting Journal Export (needs the GL mapping config — scope it as its own milestone).

**Working conventions:** propose scope before coding; keep engines/tax/pension/governance/fixtures untouched for report milestones; reports stay read-only; every report total must reconcile to the Salary Slip; run the full backend suite + all smoke checks + `npm run build`/`lint` before committing.
