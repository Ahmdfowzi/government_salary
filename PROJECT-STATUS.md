# Project Status — Iraqi Government Payroll

> Handoff snapshot. Backend = Frappe v15 app `iraqi_government_payroll` (module
> **Government Payroll**); Frontend = Next.js (App Router, Arabic RTL, Cairo).
> Validated on a live Docker bench (`docker/`), Python 3.12.

## Snapshot

| Item | Value |
|---|---|
| Current phase / milestone | **Phase 4 — M15 complete (M16 = final hardening/docs)** |
| Last completed milestone | **M15 — Accounting journal export (proposal only)** |
| Current HEAD commit | **`9645d87`** |
| Total DocTypes (Government Payroll module) | **35** |
| Backend tests passing | **205** (`python3 -m unittest`, no bench) |
| Smoke checks passing | **10 / 10** (live bench, `bench execute`) |
| Frontend build (`npm run build`) | **✓ passing** |
| Frontend lint (`npm run lint`) | **✓ passing** (no warnings/errors) |
| Working tree | clean |

Smoke checks (all exit 0): `governance` · `locking` · `api` · `create` ·
`reports` · `pension_report` · `bank_transfer` · `excel_export` · `pdf_export` ·
`accounting_journal`
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
| **M14** | PDF export for all 7 reports (wkhtmltopdf + bundled Amiri OFL font, base64 `@font-face`, RTL) | `services/reports/pdf_export.py`, `services/reports/fonts/Amiri-Regular.ttf`, `reports_api.render_report_pdf` | +7 tests, live `pdf_export` smoke, Arabic verified visually | `e5429f0` |
| **M15** | Accounting journal export — **proposal only, no GL posting** | `government_payroll/doctype/payroll_account_mapping/` (Single), `services/accounting/journal_service.py`, `api/accounting_api.py`, `frontend .../accounting-journal/page.tsx` | +10 tests, live `accounting_journal` smoke, `bench migrate` | `9645d87` |

---

## Phase 4 Summary (M10–M15) — Reports & Export

Phase 4 is **complete**. It added a read-only reporting and export layer on top of
the Phase 2/3 engines and governance, with no changes to payroll calculation:

- **M10 — Payroll reports + CSV** (`0911017`): five read-only registers — Run
  Summary, Employee, Allowances, Deductions, Tax — aggregated from Salary Slip /
  Snapshot; client-side CSV. Totals reconcile to the slip (no recomputation).
- **M11 — Retirement pension register** (`6b6503e`): 15-column register from
  stored Pension Calculation / Retirement Pension Snapshot values; filtered by
  date range + status. No retirement calculation in the report.
- **M12 — Bank transfer export** (`3acd940`): per-employee net + bank details;
  added optional profile fields `iban` / `bank_name` / `national_id`; incomplete
  rows flagged, never skipped.
- **M13 — Excel export** (`029d259`): `.xlsx` for all 7 reports via openpyxl on a
  shared column-spec layer; RTL sheet, bold header/totals.
- **M14 — PDF export** (`e5429f0`): PDF for all 7 reports via wkhtmltopdf, reusing
  the M13 column specs; bundled **Amiri** (OFL) font embedded as base64
  `@font-face` for correct Arabic RTL shaping (the container ships no Arabic font).
- **M15 — Accounting journal export** (`9645d87`): balanced double-entry journal
  **proposal** from an explicit account mapping. Export only — never posts to a
  ledger.

---

## Current Exports

| Export | Scope | How | Notes |
|---|---|---|---|
| **CSV** | all 7 reports + accounting journal | client-side (`shared/services/csv.ts`) from fetched JSON | UTF-8 BOM for Arabic; no backend dependency |
| **Excel (.xlsx)** | all 7 reports + accounting journal | backend openpyxl (`xlsx_export.build_workbook`) via `export_report` / `export_journal` | RTL sheet, bold header + totals row; booleans → نعم/لا, lists comma-joined |
| **PDF** | all 7 reports | backend wkhtmltopdf (`pdf_export`) via `export_report?fmt=pdf` | RTL Arabic; bundled Amiri font (base64 `@font-face`); landscape |
| **Bank transfer** | per-employee net + bank details | CSV + Excel | every row included; incomplete (`(iban OR bank_account) AND net>0` fails) flagged with reasons, never skipped |
| **Accounting journal proposal** | per run | `journal_export` (JSON) + `export_journal` (xlsx) + CSV | balanced debit = credit; requires the account mapping; **proposal only — no GL Entry / Journal Entry, no posting** |

All exports are **read-only**: they serialize figures the engines already produced;
no export recomputes salary/tax/pension or writes back to payroll data.

---

## Known Safeguards

- **Locked runs read immutable Snapshots.** Reports, exports and the accounting
  journal read the **Payroll Calculation Snapshot** for a Locked run
  (`reports_api._rows_for` → `governance.is_locked`), guaranteeing historical
  figures cannot drift.
- **Unlocked (active) runs read the live Salary Slip.** Any non-Locked run is read
  from the current slip.
- **Accounting export is proposal-only.** `accounting_api` builds and serializes
  balanced rows; it never creates a **GL Entry** or **Journal Entry** and never
  submits anything. A unit test asserts no `get_doc`/posting occurs.
- **No GL posting anywhere.** This app has no Chart of Accounts; account codes are
  free-text in the Payroll Account Mapping Single. Nothing writes to a ledger.
- **Mapping required before accounting export.** A non-zero amount with no mapped
  account fails safely (`JournalMappingError` → `frappe.throw`); an account is
  required only when its amount is non-zero. An empty run yields a safe, balanced,
  empty journal.
- **Balanced journal by construction.** debits (salary + allowance expense) and
  credits (employee payable + pension + tax + other) both equal Σ earnings;
  an imbalance raises `JournalImbalanceError` (data-integrity net).
- **PDF Arabic.** The bench container has no Arabic font, so PDFs embed the bundled
  open-source **Amiri** (OFL) font as a base64 `@font-face`; Arabic RTL rendering
  was verified visually before adopting the approach.

---

## Current System State

- **Governance workflow:** ✅ Complete. Server-enforced state machine + RBAC + immutable audit log; REST API + UI; run creation. Every transition checks role (M4) and writes one immutable event (M5); a failed audit insert aborts the transition.
- **Reports:** ✅ 5 payroll registers (Run Summary, Employee, Allowances, Deductions, Tax) — read-only, sourced from Salary Slip (active) / Snapshot (locked); totals reconcile to the slip (no recomputation). CSV + Excel export.
- **Pension register:** ✅ Retirement Pension Register (15 columns), filtered by `from_date`/`to_date`/`status`; reads stored Pension Calculation values, immutable Retirement Pension snapshot for finalized records. No retirement calculation in the report.
- **Bank transfer:** ✅ Per-employee net (Slip/Snapshot) + profile bank details; every row included; incomplete rows **flagged not skipped**. CSV + Excel.
- **Excel export:** ✅ All 7 reports via backend openpyxl (no new dependency, no SheetJS). RTL sheet, bold header/totals; booleans → نعم/لا, lists joined; downloaded via a browser GET to `export_report`.
- **PDF export:** ✅ All 7 reports via backend wkhtmltopdf, reusing the M13 column specs. RTL Arabic with the bundled Amiri (OFL) font (base64 `@font-face`); landscape; `export_report?fmt=pdf`.
- **Accounting journal:** ✅ Proposal-only balanced double-entry journal per run, from an explicit Payroll Account Mapping. Locked→Snapshot / active→Slip. **No GL posting.** JSON + Excel + CSV.

---

## Deferred / Out of Scope (future, not started)

Phase 4 (M10–M15) is complete; nothing is pending within it. Items below are
explicitly **out of the current product scope** and would be separate future work:

- **Real ledger integration / GL posting.** The accounting journal is a proposal
  only. Posting to an actual general ledger (e.g. an ERPNext Journal Entry) is
  deliberately excluded.
- **Chart of Accounts.** Account mapping uses free-text codes; no Account DocType.
- **Live-bench frontend walkthrough.** UI is verified via `next build`/`lint` +
  the live API/export smoke checks; an end-to-end browser session against a
  logged-in bench (CORS + session) remains a manual step.

---

## Known Technical Notes

- **Python 3.12 pin (required).** Frappe v15 supports Python 3.10–3.12 only. The `frappe/bench` image defaults to **3.14**, which breaks the document-save `file_lock` path. `docker/install-app.sh` pins the bench virtualenv to **3.12.12** and self-heals an existing env (site/DB preserved). Do **not** run on 3.13/3.14.
- **`is_locked` shadowing (resolved in M5.3).** A controller method named `is_locked()` shadowed Frappe's `Document.is_locked` **property**, which `check_if_locked()` evaluates as a boolean on every save → a bound method is always truthy → `lock_age().stat()` on a non-existent lock → `FileNotFoundError`, breaking every save on a real bench. **Fix:** renamed to `is_run_locked()`; a regression test asserts the class does not define `is_locked`. **Rule:** never name a controller method the same as a Frappe `Document` property/method (`is_locked`, `is_new`, …); fake-frappe unit tests won't catch it — only a live bench will.
- **Snapshot vs Salary Slip source selection.** Reports read the **live Salary Slip** for an **active** run and the **immutable Payroll Calculation Snapshot** for a **Locked** run (`reports_api._rows_for` → `governance.is_locked`). For the pension register, **finalized (status Approved)** records read monetary figures from the immutable **Retirement Pension snapshot** (identity/metadata stay from the live record; `service_years` recovered from the snapshot's stored `service_months`). Net salary is always read, never recomputed.
- **Bank transfer completeness.** A row is `bank_complete` only if **(iban OR bank_account) AND net > 0**; otherwise it is included with `bank_complete=false` and a `missing` reasons list — never silently skipped. In Excel, `bank_complete` renders نعم/لا and `missing` joins with "، ".
- **openpyxl on the host for tests.** openpyxl is a transitive Frappe dependency (present in the bench, **not** added to `requirements.txt`). The host test machine needs it to reopen workbooks in `test_reports.py`: `pip install openpyxl`.
- **Bundled Amiri font for PDF (M14).** The bench container has no Arabic-capable font, so PDFs would render boxes. Fix: the open-source **Amiri** font (OFL) is bundled at `services/reports/fonts/Amiri-Regular.ttf` and embedded as a base64 `@font-face` data URI in the report HTML — self-contained, independent of container fonts. Packaged via the existing `MANIFEST.in recursive-include`. `poppler-utils` was installed in the container for **visual verification only** — it is **not** an app dependency; runtime PDF needs only `wkhtmltopdf` (already present).
- **Accounting journal is proposal-only (M15).** `services/accounting/journal_service.build_journal` is pure (no Frappe); `api/accounting_api` only reads (slips/snapshots + the Payroll Account Mapping Single) and serializes. It never creates a GL/Journal Entry and never submits. Balance holds by construction: debits (salary + allowance expense) = credits (employee payable + pension + tax + other) = Σ earnings. Source selection reuses `reports_api._rows_for` (Locked→Snapshot, active→Slip).

---

## Resume Instructions

Phase 4 (M10–M15) is complete and hardened. There is **no pending product scope**;
resume by confirming the baseline, then scope any new work as its own milestone.

1. **Confirm a clean baseline.**
   - `git -C "<repo>" log --oneline -1` → expect `9645d87` (Phase 4 M15); working tree clean.
   - Backend tests: `cd backend/iraqi_government_payroll/iraqi_government_payroll/tests && python3 -m unittest discover -p 'test_*.py'` → **205 OK** (install openpyxl on the host first if absent: `pip install openpyxl`).
   - Frontend: `cd frontend && npm run build && npm run lint` → both pass.
2. **Bring up the live bench if needed.** `docker compose -f docker/docker-compose.yml up -d`, then `docker compose ... exec frappe bash /mnt/scripts/install-app.sh` (pins Python 3.12, migrates, prints fixture counts: 143/16/4/9/6, **35 DocTypes**).
3. **Re-run the 10 smoke checks** (all should exit 0):
   `for c in governance locking api create reports pension_report bank_transfer excel_export pdf_export accounting_journal; do docker compose -f docker/docker-compose.yml exec frappe bash -lc "cd ~/frappe-bench && bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.$c"; done`
4. **New work is future scope** (see "Deferred / Out of Scope"): real GL posting, a Chart of Accounts, or a browser end-to-end pass. Each should be a separate, explicitly-approved milestone — not part of Phase 4.

**Working conventions:** propose scope before coding; keep engines/tax/pension/governance/fixtures untouched for report/export milestones; exports stay read-only and never recompute payroll; every report total must reconcile to the Salary Slip; the accounting journal stays a proposal (no GL posting); run the full backend suite + all 10 smoke checks + `npm run build`/`lint` before committing.
