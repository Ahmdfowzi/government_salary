# Engine Boundaries & Runtime Safety

Reference for how the calculation engines are layered, where each one starts and
stops, the `confirmed=false` contract, the runtime-safety guarantees of the
controller hooks, and the current PC (pending-clarification) limitations.

---

## 1. Engine layers (M3 → M7)
All engines are **pure Python** under `services/` (no Frappe in the math path);
Frappe wiring lives in `services/payroll_engine/repository.py` (lazy `import
frappe`). Data access is separated from calculation so every engine is unit
tested against the fixtures without a bench.

| Layer | Module | Input → Output | Notes |
|---|---|---|---|
| **M3 Active Salary** | `payroll_engine/engine.py`, `allowance/allowance_service.py` | profile + rule set → basic + allowances + **200% cap** → gross | percentages on **basic only**; cap = **2 × basic** (capped allowances ≤ 200% of basic) |
| **M4 Tax** | `tax/tax_service.py` | annual taxable → progressive brackets → monthly tax | from **Income Tax Bracket only**; `round_iqd` half-up; `DED_TAX` is presentation-only |
| **M4 Pension** | `pension/pension_service.py` | active deduction; Article-21 retirement pension | 36-mo avg · 2.5% · 100% cap · cert allowance · COL · tax · EOS |
| **M5 Net Salary** | `payroll_engine/net_salary.py` | active gross − pension deduction − tax − other → net | composite `engine_versions`; `round_iqd` applied only at this Salary Slip boundary |
| **M6 Increment/Promotion** | `increment/…`, `promotion/…` | profile state → mutated profile state | **inputs only** — no pay recompute; Salary Slip re-reads the profile later |
| **M7 Payroll Run** | `payroll_engine/payroll_run.py` | period + profiles → draft Salary Slips | idempotent batch over M5; draft only (no submit, no snapshot) |

**Golden rules:** rule set chosen by period date · percentages on basic only · no
calculation in the frontend · every figure traceable to its source rule · final
slip money rounded with `round_iqd`.

## 2. `confirmed=false` contract (uniform across all engines)
- **value present + confirmed=false** → compute and mark **provisional** (flag propagates to the net result / slip).
- **value empty + confirmed=false** → **skip** the component and emit a **warning**.
- **no matching rule** (e.g. certificate for an uncovered qualification) → **0 + note**, never an error.
- **Missing legal values are never invented** (no silent zero-substitution of a real rate).

## 3. Runtime safety review (controller hooks)
| Hook | Behaviour | Safety |
|---|---|---|
| `Salary Slip.validate` | Recomputes & populates fields from the engines on every save | Intended (draft calculation); deterministic, no side effects beyond the slip |
| `Salary Slip.on_submit` | Writes one immutable Salary Slip snapshot | **Guarded**: skips if a `Salary Slip` snapshot already exists for the slip |
| `Payroll Run.run_batch()` | Manual method; builds **draft** slips, tallies results | **Not** triggered on save; no auto-execution; never submits slips |
| `Annual Increment Request.on_submit` | Applies increment to the profile + snapshot | **Guarded**: refuses if an `Annual Increment` snapshot already exists for the request; profile-state dates also prevent re-increment |
| `Promotion Request.on_submit` | Applies promotion to the profile + snapshot | **Guarded**: refuses if a `Promotion` snapshot already exists for the request; grade-date also prevents re-promotion |
| `Pension Calculation` controller | `validate`/`on_submit` are **stubs** | Retirement pension is computed by the pure service on demand; the controller intentionally does **not** auto-compute on save |
| `Payroll Calculation Snapshot` | `on_update`/`on_trash` block edits & deletes | Immutable at the application layer |

Guarantees: no unintended recalculation except the intended Salary Slip draft
calc; no snapshot duplication; no profile mutation outside the increment/
promotion submit hooks; no payroll-run auto-execution on save.

## 4. Idempotency guards
- **Salary Slip snapshot** — one per slip (`frappe.db.exists` on `salary_slip` + type).
- **Payroll Run** — `FrappeSlipStore.upsert` finds the existing draft by (period, employee); re-running updates, never duplicates.
- **Increment/Promotion** — applying a request twice is blocked by a snapshot guard keyed on `source_request`; re-applying to an already-mutated profile is additionally a no-op (eligibility dates).
- Pure predicate `audit_service.snapshot_is_duplicate(...)` mirrors the frappe guard and is unit tested.

## 5. Current PC limitations (provisional / pending official values)
| PC | Item | Effect today |
|---|---|---|
| PC-1 | 2008 salary scale | IRAQ-2008 rule set empty |
| PC-2 | Geographic areas | none loaded |
| PC-3 | Risk % per job | `RISK_DEFAULT` range only, skipped (confirmed=false) |
| PC-4 | Spouse/child amounts | valued but provisional |
| PC-5 | Geographic in 200% cap | parameter "Undecided" |
| PC-6 | Pension contribution rate | **pension deduction omitted (0) + warning** until set |
| PC-7/8 | Tax legal allowances / life insurance | **tax computed on full gross**; `INCOME_TAX` flagged provisional |
| PC-9 | Cost-of-living method | retirement COL = 0 + warning unless configured |
| PC-10 | Overtime formula | overtime not computed |
| PC-12 | Extra study years cap | not applied |
| PC-13/14 | Absence / stamps deductions | not computed |

When an official value arrives, set it on the relevant rule/parameter and flip
`confirmed=true` — **no code change required**; the engines pick it up.

## 6. Open design question (carried)
Whether the active-salary pension contribution is **pre-tax** (reduces the tax
base) is unconfirmed. Current behaviour: pension deduction does **not** reduce
the tax base. Revisit when confirmed.
