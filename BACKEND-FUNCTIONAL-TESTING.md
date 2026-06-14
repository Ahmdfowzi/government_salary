# Backend Functional Testing — Iraqi Government Payroll

End-to-end validation of the government payroll backend after the financial-wiring
audit (`FINANCIAL-WIRING-AUDIT.md`). UI was not touched. Calculation logic was not
refactored — no test proved a bug.

**Result: 290 host unit tests + 18 live smoke checks pass (0 failures).**
This round added **23 host tests** (`test_salary_cases.py`, `test_pension_cases.py`)
and **1 smoke check** (`data_integrity`); the rest of the matrix was already covered.

| Final counts | Before | After |
|---|---|---|
| Host unit tests | 267 | **290** |
| Live smoke checks | 17 | **18** |

---

## 1. Data Integrity — PASS
Smoke `data_integrity` (new) + `grade_validation`:
- Active rule set present (IRAQ-2015, status Active).
- Government Grades master complete (13 active grades).
- Salary-scale coverage: active scale for IRAQ-2015 with **143 grade/stage rows, all
  priced** (basic > 0).
- Grade/Stage validation: an invalid placement (e.g. grade 7 / stage 99) is rejected
  with an Arabic message at profile save.
- Profile required fields: a profile without a grade is rejected (mandatory).
- Position linkage: `government_position` resolves to the Arabic position title.
- Entity linkage: `government_entity` resolves to the Arabic entity name; the tree
  parent chain resolves (ministry/department).

## 2. Salary Calculation — PASS
Host `test_salary_cases.py` (new, 14) + `test_active_salary.py` (20) + `test_tax_pension.py` (13):

| Case | Coverage |
|---|---|
| Grade 1 Stage 1 | basic 910,000 ✓ |
| Grade 5 Stage 5 | basic 453,000 ✓ |
| Grade 7 Stage 1 | basic 296,000, gross 429,200 ✓ |
| Grade 10 Stage 11 (max stage) | basic 200,000 ✓ |
| Special grade (SPECIAL_A) | basic 2,413,000 ✓ |
| Married employee | + FAM_SPOUSE 50,000 ✓ |
| Employee with children | + FAM_CHILD 10,000 × count (capped at 4) ✓ |
| Missing family data | no family allowances, calc still valid ✓ |
| Missing grade/stage | raises `PayrollError` (never silent 0) ✓ |
| Missing rule set (period out of range) | raises `PayrollError` ✓ |

Verified per case: **basic salary**, **allowances**, **200% cap** (capped total ≤ 2×basic
for every grade/stage), **pension deduction**, **income tax**, **net salary**
(net = gross − pension − tax − other; deductions reconcile), **snapshot payload**
(input/output snapshot structure), and **Arabic/English validation messages** (engine
raises `PayrollError`; the Frappe controllers + `ensure_calculable` raise the AR/EN
messages — covered by the `grade_validation` and `financial_wiring` smokes).

## 3. Promotion — PASS
Host `test_increment_promotion.py` (promotion half) + smoke `grade_validation` (live apply):
- Eligible promotion (grade 7 → 6) ✓; Not eligible (before duration) ✓.
- Promotion duration rules / stage placement (equal, next-higher, below-first) ✓.
- Grade update + Stage update + **Salary basis update** (new basic from the scale) ✓.
- Senior grade does not auto-promote ✓.
- Snapshot creation (Promotion snapshot payload) ✓.
- Audit history (request from/to grade, stages, old/new salary) ✓.
- Live: promotion changes the grade Link + stage **without touching Government
  Position** (grade is not derived from Position).

## 4. Annual Increment — PASS
Host `test_increment_promotion.py` (increment half) + smoke `grade_validation` (live apply):
- Eligible increment (stage 1 → 2) ✓; Not eligible (before 12 months) ✓.
- Stage increase (employee-level Int) ✓.
- Max stage handling (stage 11 → warning, no over-advance) ✓.
- `current_stage_date` updated ✓; Snapshot creation ✓; Audit history ✓.

## 5. Pension — PASS
Host `test_pension_cases.py` (new, 9) + `test_tax_pension.py`:
- Service years 15 / 20 / 30 / 35 → approved pension 378,750 / 505,000 / 757,500 /
  883,750 (accrual 2.5%/yr, monotonic, capped at 100% of last functional salary).
- Bachelor / Master / Doctorate certificate = 10% / 15% / 20% of approved (increasing).
- Cost-of-living: applied when configured, 0 when missing.
- End-of-service: 0 below 30 years, last_full_salary × 12 at/above 30 years.
- Pension tax (monthly) ≥ 0; **net pension** = gross − tax − other (reconciles).

## 6. Payroll Run workflow — PASS
Smoke `governance` (Draft → Calculated → Under Review → Approved → Submitted),
`locking` (→ Locked, unlock, historical integrity), `financial_wiring`, `demo`
(active/completed/locked runs); host `test_payroll_run.py`, `test_governance.py`:
- Employee inclusion (only Active, in scope, by rule set) ✓.
- Per-employee calculation ✓; **error isolation** (one bad employee does not abort the
  batch; run marked Failed only if all fail) ✓.
- Totals aggregated from the **immutable snapshots** of a locked run ✓.
- Lock prevents modification (recalculation/delete blocked after lock) ✓.
- Unlock only by the allowed role (Administrator) ✓.
- Historical integrity (locked snapshot net unchanged after later profile edits) ✓.

## 7. Reports & Export — PASS
Smoke `reports`, `bank_transfer`, `excel_export`, `pdf_export`, `accounting_journal`,
`pension_report`, `payroll_slip`, `locking`, `demo`; host `test_reports.py` (31),
`test_accounting.py` (10):
- Payroll report (run summary), Employee salary register, Pension register,
  Promotion/Increment requests, Bank transfer, Accounting journal, CSV, Excel, PDF.
- `reports_api._rows_for(run)` reads the **Payroll Calculation Snapshot** for a locked
  run, else the live Salary Slip; every export path goes through it, so locked-run
  outputs are from immutable data and the journal balances (debit = credit).

## 8. Permissions — PASS
Smoke `security`; host `test_security.py` (11), `test_authorization.py` (18),
`test_api_governance.py` (24):
- Government Payroll Administrator / Payroll Administrator — full create/write.
- Payroll Manager — approves/submits/cancels (the "reviewer/approver" role in this
  system; there are no separate `Payroll Reviewer`/`Payroll Approver` DocRoles — the
  governance matrix maps reviewer→submit_for_review, approver→approve to Payroll
  Manager / Administrator).
- Payroll Officer — read-only on profiles; HR Officer/User — write on employee data.
- Finance Officer/User — read + export; Auditor / Read Only User — read-only.
- The accounting-journal export gate denies Read Only User, allows Finance.

---

## Failing tests
**None.** All 290 host tests and 18 smoke checks pass.

## Real backend bugs found & fixed
**None this round.** The financial-wiring audit (prior commit) had already added the
pre-calc guard and the run-path family/grade snapshot completeness. Functional testing
confirmed the calculation chain across the full matrix; no calculation logic was changed.

## New tests added
- `tests/test_salary_cases.py` — grade/stage matrix, family variants, missing-data errors,
  snapshot payload (14 tests).
- `tests/test_pension_cases.py` — service-year sweep, certificate levels, COL/tax/net (9).
- `smoke/checks.py:data_integrity` — rule set / grade master / scale coverage /
  grade-stage validation / required fields / position+entity linkage (1 smoke).
