# Financial Wiring Audit — Iraqi Government Payroll

Scope: confirm that the Frappe backend does not merely store DocTypes but actually
computes salary, allowances, deductions, tax, pension, promotion impact, payroll-run
totals, immutable snapshots and accounting values, with the financial links between
DocTypes correctly connected.

**Headline:** the financial engine is substantially wired and test-covered (260 host
unit tests + 16 live smoke checks before this audit). Calculation is done in a pure
Python services layer (no Frappe in the math path), with Frappe controllers handling
persistence, validation and the governance workflow. No controller files are missing.
Two genuine hardening gaps were found and fixed (see §9–§11).

---

## 1. DocTypes — controller presence

Every DocType has a Python controller file. Controllers fall into two correct
categories:

**Business-logic controllers** (validate / on_submit / immutability / workflow):
- `Government Employee Payroll Profile` — grade↔grade_code sync, (grade, stage) scale
  validation, family/dependent recompute.
- `Payroll Run` — full governance state machine (calculate → review → approve →
  submit → lock), role checks, audit events.
- `Payroll Calculation Snapshot` — immutability guards (on_update/on_trash block edits
  to locked snapshots).
- `Salary Slip` — recompute on save, writes the immutable snapshot on submit.
- `Pension Calculation`, `Promotion Request`, `Annual Increment Request` — apply via
  the engine + write snapshots.
- `Government Rule Set`, `Government Salary Scale`, `Government Entity`, `Payroll
  Period`, `Qualification Appointment Rule`, `Allowance Rule` — validation.

**Pure data containers** (correctly `pass` — no business logic belongs here):
Government Grade, Government Position, Government Salary Scale Detail, Income Tax
Bracket, Pension Rule, Promotion Rule, Annual Increment Rule, Tax Allowance Rule,
Geographic Area, Rule Set Parameter, Payroll Account Mapping, Government Payroll
Settings, Family Member Dependent, all child tables (`* Line`, Promotion Grade
Duration, etc.). These are read by the services layer.

→ **No missing controller files.**

## 2. Where the business logic lives (services layer)

| Service | Responsibility |
|---|---|
| `payroll_engine/engine.py` | active salary: basic + allowances + 200% cap → gross |
| `payroll_engine/net_salary.py` | gross − pension − tax − other → **net** |
| `payroll_engine/scale_resolver.py` | grade+stage → basic salary; placement validation |
| `payroll_engine/rule_resolver.py` | period date → active rule set |
| `allowance/allowance_service.py` | certificate/position/risk/family allowances + cap |
| `tax/tax_service.py` | progressive income-tax brackets (annual → monthly) |
| `pension/pension_service.py` | pension **deduction** + **retirement pension** |
| `increment/increment_service.py` | annual increment (stage advance) |
| `promotion/promotion_service.py` | promotion (grade/stage/salary change) |
| `family/family_service.py` | dependent ages / eligibility / counts |
| `audit/audit_service.py` | builds the immutable Payroll Calculation Snapshot |
| `accounting/journal_service.py` | balanced accounting journal (proposal only) |
| `reports/report_service.py` | registers; reads slips/snapshots, never recomputes |
| `payroll_engine/repository.py` | the only Frappe-wiring layer (lazy `import frappe`) |

→ **No missing service files.**

## 3. Financial links between DocTypes

```
Payroll Period ──date──▶ Government Rule Set (active by period date)
Government Rule Set ──1:N──▶ Government Salary Scale (is_active)
Government Salary Scale ──child──▶ Salary Scale Detail (grade_code, stage, basic_salary)
Government Grade ◀──Link── Profile.grade / Salary Scale Detail.grade_ref
Profile (rule_set, grade, stage, qualification, marital, dependents)
   └─▶ engine resolves basic from Scale Detail by (grade, stage)
Allowance Rule (rule_set, match_key, context=Active) ──▶ allowance lines
Allowance Rule (component_code=DED_PENSION) ──▶ pension deduction
Income Tax Bracket (rule_set) + Tax Allowance Rule ──▶ income tax
Pension Rule (rule_set) + Pension Certificate allowances ──▶ retirement pension
Promotion Rule / Annual Increment Rule (rule_set) ──▶ promotion / increment
Payroll Run ──▶ Salary Slip (draft) ──submit──▶ Payroll Calculation Snapshot (immutable)
Reports / Bank Transfer / Accounting Journal / PDF / Excel ──▶ read Snapshot (locked) or Slip
```

**Clarification of four names in the request that are NOT separate DocTypes (by design,
not broken links):**
- **Deduction Rule** — deductions are modelled as `Allowance Rule` rows with
  `allowance_type = "Deduction"` (codes `DED_PENSION`, `DED_TAX`, `DED_LOAN`, …). Tax and
  pension deductions are computed by their dedicated engines; ad-hoc deductions
  (loan/penalty/absence) enter as the `other_deductions` input. There is no separate
  "Deduction Rule" DocType and none is required.
- **Salary Calculation Log** — renamed to **`Payroll Calculation Snapshot`** (the
  immutable audit record). No separate log DocType.
- **Bank Transfer** — a read-only **endpoint** `reports_api.bank_transfer(run)`, not a
  DocType. Reads net from the Snapshot/Slip + bank fields from the profile.
- **Accounting Journal** — a read-only **endpoint** `accounting_api.journal_export(run)`
  (proposal only; no GL posting), not a DocType.

→ **No broken links.** All other named DocTypes exist and are connected as above.

## 4. Salary calculation inputs — confirmed

`compute_net_salary(ctx, emp)` uses, in order: active **rule set** (by period date) →
active **salary scale** → **grade + stage** → **basic salary** → **allowance rules**
(certificate by qualification, position, risk, **family** by spouse/children) → 200%
cap → gross → **pension deduction** rule → **income-tax brackets** (+ Art.12 tax
allowances) → net. **Family/dependent data** feeds it: `eligible_children_count` drives
the child allowance and the taxpayer status/dependents feed the tax allowances.

## 5. Promotion Request — confirmed

`promotion_service.compute_promotion` + `repository.apply_promotion` update **grade**
(grade_code + grade Link), **stage**, **salary basis** (new basic from the scale),
write an immutable **Promotion snapshot**, and record **audit history** (the request
stores from/to grade, stages, old/new salary). Promotion does **not** derive grade from
Government Position.

## 6. Pension Calculation — confirmed

`pension_service.compute_retirement_pension` uses **last full salary**, **36-month
average**, **service years/months**, **accrual rate + cap**, **certificate allowance**
(by qualification), **cost-of-living allowance**, **income tax**, **end-of-service
bonus** (last_salary × 12 when service ≥ minimum), and **net pension**.

## 7. Payroll Run aggregation — confirmed

`run_payroll` builds a draft Salary Slip per Active in-scope employee and tallies
employee/processed/success/warning/error counts on the run. **Financial totals** (basic,
allowances, deductions, tax, pension, net, employee count, total payroll cost) are
aggregated **on demand** by `reports_api.run_summary` from the immutable Snapshot
(locked) or Slip (active) — deliberately **not** duplicated onto the run row, so there is
a single source of truth. Locked runs are immutable.

## 8. Reports / Bank / PDF / Excel / Accounting read immutable data — confirmed

`reports_api._rows_for(run)` returns Snapshot rows when `governance.is_locked(state)`,
else live Slip rows. Run summary, employee/allowance/deduction/tax registers, bank
transfer, PDF, Excel and the accounting journal all go through this, so a **locked**
run's outputs are read from the immutable Payroll Calculation Snapshot, never from live
mutable employee data. The printable Government Payroll Slip is likewise built from the
Snapshot.

## 9. Missing controller files — NONE
## 10. Missing service files — NONE

## 11. Gaps found and fixed in this audit

1. **No upfront pre-calculation guard.** Previously, if a run's rule set had no active
   salary scale (or no eligible employees), the batch still started and every employee
   failed individually with `No salary scale row …`; the run ended `Failed`. This is
   safe but not a clean signal. **Fix:** `repository.ensure_calculable(run)` runs before
   the batch and raises a single clear message if the rule set is missing/has no active
   scale, or if no eligible Active employee is in scope. Invoked from
   `Payroll Run.calculate_run` and `repository.run_payroll`.
2. **Run path did not snapshot full family state / grade Link.** The batch fetched only
   `grade_code` and `eligible_children_count`; the new `grade` Link and the broader
   dependents summary were not carried into run snapshots (the child allowance still
   worked via `eligible_children_count`). **Fix:** the batch now also fetches the `grade`
   Link and the dependent counts, and `employee_input_from_profile` records the full
   `family_summary`, so run snapshots are immutably complete and consistent with the
   single-employee path.

## 12. Tests

- Host (`tests/test_financial_wiring.py`, added): end-to-end chain
  (rule set → scale → grade/stage → basic → allowances → cap → gross → pension → tax →
  net) on the fixtures; family→child-allowance link; run-batch aggregation with a fake
  slip store; report/snapshot immutability of recorded inputs.
- Existing suites continue to cover the engine (active salary, tax, pension, increment,
  promotion), locking/governance, reports, accounting, family.
- Smoke (`smoke/checks.py:financial_wiring`, added): a live calculate run on the bench —
  asserts net = gross − deductions from the Snapshot, the pre-calc guard blocks an
  un-scaled rule set, and locked-run reports read the Snapshot.

## 13. UI — untouched

No frontend files were modified in this audit.

---

### Optional follow-ups (not blocking; not implemented to avoid duplicating the source of truth)
- Persisting aggregate financial totals on the Payroll Run row (currently computed on
  demand from the Snapshot). Left out so the Snapshot remains the single source of truth.
- Ad-hoc per-employee deductions (loan/penalty/absence) currently enter via
  `other_deductions`; a dedicated "Employee Deduction" transactional DocType could feed
  it if recurring deductions need to be tracked.
