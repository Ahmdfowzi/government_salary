# UAT Demo Cycle — Iraqi Government Payroll

End-to-end User Acceptance Testing, driving the system as a real payroll user across
realistic personas on the live bench (not only unit/API tests). No backend calculation
logic was changed; no fake data was added to hide issues. The cycle is automated and
repeatable as `smoke/checks.py:uat_demo_cycle` (and was executed live for this report).

**Result: PASS. No bugs found (Critical / High / Medium / Low: 0).**
Final: **290 host tests · 20 smoke checks · frontend lint + build green (23 routes).**

---

## 1. Demo employees created (8 personas, committed `UAT-*`)
All under a `UAT-ENTITY` ("دائرة الاختبار (UAT)"), rule set IRAQ-2015:

| # | Number | Persona | Grade/Stage | Marital | Notes |
|---|---|---|---|---|---|
| 1 | UAT-01-SINGLE | Single | 7 / 1 | Single | — |
| 2 | UAT-02-MARRIED | Married | 7 / 1 | Married | spouse allowance |
| 3 | UAT-03-FAMILY | Married + 3 children | 7 / 1 | Married | spouse + child allowances |
| 4 | UAT-04-INCR-Y | Increment **eligible** | 7 / 2 | Single | stage date −2 yrs |
| 5 | UAT-05-INCR-N | Increment **not eligible** | 7 / 3 | Single | stage date today |
| 6 | UAT-06-PROMO-Y | Promotion **eligible** | 7 / 1 | Single | grade date −5 yrs |
| 7 | UAT-07-PROMO-N | Promotion **not eligible** | 7 / 1 | Single | grade date today |
| 8 | UAT-08-RETIRE | Near retirement / pension | 3 / 5 | Married | appointed −38 yrs |

"Invalid/incomplete profile" is exercised by attempting an invalid placement (grade 7 /
stage 99) — the system **correctly rejects** it (it is never persisted), see §3.

## 2. Employee Profile UAT — PASS
Each persona's Entity, Position linkage, Grade, Stage, Rule Set, Qualification, Hire date,
Family status and Children count read back correctly. Verified e.g. UAT-03-FAMILY →
entity `UAT-ENTITY`, grade 7, stage 1, Married, **eligible_children_count = 3** (the
controller recomputed it from the 3 dependents). Salary preview wired (see §3).

## 3. Salary Calculation UAT — PASS
- Salary preview: grade 7 / stage 1 → **basic 296,000** (engine resolver).
- Full calculation (from the payroll run, §7) per persona — basic, allowances, pension
  deduction, tax, net all from the engine:
  - Single: **net 423,367**
  - Married: **net 473,367** (+50,000 spouse allowance)
  - Married + 3 children: **net 503,367** (+30,000 child allowance) → `single < married < family` ✓
- Invalid employee → **Arabic validation message**: «الدرجة «7» والمرحلة «99» غير موجودة في
  سلم الرواتب الفعّال…» and the save is blocked.

## 4. Annual Increment UAT — PASS
- Create request from the frontend: `/increments/new` → `create_increment_request` (draft).
- Apply (on approval/submit, via the increment engine):
  - **Eligible** (UAT-04, stage date −2 yrs): stage **2 → 3** ✓.
  - **Not eligible** (UAT-05, stage date today): apply **blocked** (not due) ✓.
- Stage update + snapshot/audit: the increment writes an immutable Payroll Calculation
  Snapshot and records old/new stage on the request.

## 5. Promotion UAT — PASS
- Create request from the frontend: `/promotions/new` → `create_promotion_request` (draft).
- Apply (on approval/submit, via the promotion engine):
  - **Eligible** (UAT-06, grade date −5 yrs > 4-yr duration): grade **7 → 6** ✓ (grade Link
    updated, NOT derived from Position).
  - **Not eligible** (UAT-07, grade date today): apply **blocked** ✓.
- Grade/stage update + snapshot/audit: immutable Promotion snapshot + request from/to fields.

## 6. Pension UAT — PASS
Created via `/pension/new` → `create_pension_calculation` (runs the existing pension engine).
Service-year sweep (avg 1,000,000; last salary 1,000,000; Master; COL 30%):

| Service yrs | Approved | Certificate (15% Master) | Cost of living | End of service | Net |
|---|---|---|---|---|---|
| 15 | 375,000 | > 0 | > 0 | 0 | > 0 |
| 20 | 500,000 | > 0 | > 0 | 0 | > 0 |
| 30 | 750,000 | > 0 | > 0 | **12,000,000** | > 0 |
| 35 | 875,000 | > 0 | > 0 | **12,000,000** | > 0 |

Approved is monotonic; EOS = last salary × 12 only at ≥ 30 years; certificate, cost-of-living,
tax and net all computed. ✓

## 7. Payroll Run UAT — PASS
Full workflow on the UAT entity (8 employees), period 2027/06:
**Draft → Calculate → Submit for Review → Approve → Submit → Lock.**
- Employees included correctly: **8** (all Active in scope).
- Per-employee calculation: each gets a slip; family personas net higher (§3).
- Error isolation: a bad employee fails alone (covered by `test_financial_wiring` /
  `financial_wiring` smoke); the pre-calc guard blocks an un-scaled rule set.
- Totals from the **immutable snapshot**: run summary employees = 8, **total_net 4,283,836**.
- Locked run cannot be modified: recalculation is **blocked** after lock ✓.
- Unlock only by the allowed role (Administrator) — enforced by the governance role gate
  (`test_locking` / `locking` smoke).

## 8. Reports UAT — PASS (all read the Snapshot for the locked run)
On the locked UAT run: Employee register (8 rows), Bank transfer (8 rows), Accounting
journal (**balanced**, debit = credit). Report net == run-summary net (snapshot
consistency). Payroll/Pension/Promotion lists, CSV/Excel/PDF exports are covered by the
`reports`, `pension_report`, `bank_transfer`, `excel_export`, `pdf_export`,
`accounting_journal` smokes — all read the immutable Payroll Calculation Snapshot for
locked runs via `reports_api._rows_for`.

## 9. Permission UAT — PASS
Enforced by DocType permissions + the governance role gate (covered by `security`,
`test_security`, `test_authorization`, `test_api_governance`):
- Government Payroll Administrator / Payroll Administrator — full create/write.
- Payroll Manager — approves/submits/cancels (the reviewer/approver role; there are no
  separate `Payroll Reviewer`/`Payroll Approver` DocRoles).
- Payroll Officer — read-only on profiles; HR User — write on employee data.
- Finance User — read + export; Auditor / Read Only User — read-only.
- Forbidden actions are denied at the backend (e.g. Read Only User cannot create a profile
  or export the accounting journal); the UI also hides them via role helpers.

## 10. UX UAT — PASS (code-level; visuals confirmed in earlier sessions)
- Arabic RTL (`<html dir="rtl">`, `text-right` tables), Cairo font (app + slip PDF),
  English numerals (`.num`), responsive grids (`sm:`/`lg:`), tables in `overflow-x-auto`,
  loading/empty/error states on every data page, clear Arabic action buttons.

---

## Bugs found by severity
**None.** Critical: 0 · High: 0 · Medium: 0 · Low: 0. The system passed the UAT cycle
cleanly across all 8 personas and 10 categories.

## Fixes implemented
**None required** — no UAT bug surfaced; no backend calculation logic changed.

## Observations (informational, not bugs)
- An invalid/incomplete profile is **prevented** at save (Arabic message), so it cannot be
  persisted — this is the intended safeguard, exercised as the rejection case.
- "Payroll Reviewer/Approver" are not distinct roles; the governance matrix maps
  reviewer→submit_for_review and approver→approve onto Payroll Manager / Administrator.

## Final results
- **Demo employees:** 8 `UAT-*` personas created (committed) under `UAT-ENTITY`.
- **Host tests:** 290 (pass).
- **Smoke checks:** 20 (pass) — incl. the new `uat_demo_cycle`.
- **Frontend build:** lint ✓, build ✓ (23 routes).
