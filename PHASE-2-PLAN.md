# Phase 2 Plan — Iraqi Government Payroll

> **Status:** APPROVED (planning). Implementation NOT started.
> **Core principle:** rules are *data*, not code. Every legal value is versioned and reproducible; anything marked **PC-x** stays a configurable row with `confirmed = false` — the engine runs on a provisional value and flags it, never guesses.

---

## 0. Approved architectural decisions (apply at start of M1)

1. **Versioning spine — `Government Rule Set`.** Keep all rule DocTypes normalized and separate, but place every legal rule under a versioned `Government Rule Set` envelope (named, status-gated, `effective_from`/`effective_to`). The engine resolves **one** rule set by payroll-period date, then reads all members within it. Per-row effective dates are dropped in favor of the set's window — amendments = clone → new version → publish (never silently edit an Active rule).
2. **Reproducibility — `Payroll Calculation Snapshot`.** Every calculation writes one immutable snapshot pinning `rule_set` (+ version), `engine_version`, and a full `input_snapshot`, so `reproduce(output) = engine(engine_version) × rule_set(version) × input_snapshot`.
3. **Organization — single `Government Entity` NestedSet tree** with `entity_type ∈ {Ministry, Authority, Governorate, Directorate, Department, Division, Unit}` and `parent_government_entity` (self-link). Parent→child nesting validated.
4. **Roles — `Government Position` master** drives position allowance and promotion vacancy checks; employee profile links to it.
5. **Settings split:** legal knobs live in the Rule Set (`Rule Set Parameter` child); only operational toggles stay in the `Government Payroll Settings` Single.

### Renames — APPROVED, rename in place, no aliases (execute first in M1)
- `Government Salary Law` → **`Government Rule Set`** (generalized from "scale version" to "complete legal package version").
- `Salary Calculation Log` → **`Payroll Calculation Snapshot`** (+ `rule_set`, `engine_version`, full input snapshot).
- Link cascade: `salary_law` → `rule_set` on Salary Scale, Qualification Appointment Rule, Allowance Rule, Employee Payroll Profile.

> These renames are **not yet performed** — they are scheduled as the very first M1 task. Nothing in the codebase has been edited for Phase 2.

---

## 1. Legal rules inventory

`Data` = fixture/rule row. `Logic` = engine algorithm (reads data). ✅ ready · ⚠️ pending (PC-x).

| # | Rule | Source | Data/Logic | Status | Lands in |
|---|------|--------|-----------|--------|----------|
| R1 | 2015 salary scale (3 senior + 10 regular × 11 = **143 rows**) | D1 | Data | ✅ | Salary Scale |
| R2 | 2008 salary scale | D2 | Data | ⚠️ PC-1 | Salary Scale (empty) |
| R3 | Stage formula `stage_n = stage_1 + (n-1)·incr` (validation only) | D1 | Logic | ✅ | engine verify |
| R4 | Annual increment = +1 stage after 12 months; amount per grade | D1 | Data+Logic | ✅ | Annual Increment Rule / scale |
| R5 | Appointment by qualification/specialization (**16 rows**) | D1 | Data | ✅ | Qualification Appointment Rule |
| R6 | Extra study years → +1 stage per recognized year | D1 | Logic+cfg | ⚠️ PC-12 | engine + Rule Set Param |
| R7 | Certificate allowance **active** (7 rates, on Basic, capped) | D1 | Data | ✅ | Allowance Rule |
| R8 | Position allowance (5 rates, on Basic, capped) | D1 | Data | ✅ | Allowance Rule + Government Position |
| R9 | Risk allowance 20–30% (capped) | D1 | Data | ⚠️ PC-3 | Allowance Rule (per job) |
| R10 | Craft allowance 15% (capped) | D1 | Data | ✅ | Allowance Rule |
| R11 | Spouse 50,000 / Child 10,000 (max 4), non-capped | D2 | Data | ⚠️ PC-4 | Allowance Rule |
| R12 | Geographic fixed amount per area | D2 | Data | ⚠️ PC-2 | Geographic Area |
| R13 | Geographic inside 200% cap? | D2 | Logic flag | ⚠️ PC-5 | Rule Set Parameter |
| R14 | Overtime ≤ 3h/day, non-capped; hourly formula | D1 | Data+Logic | ⚠️ PC-10 | Rule Set Param + engine |
| R15 | 200% cap + capped/non-capped classification | D1/D2 | Logic + flag | ✅ | engine + Allowance Rule |
| R16 | Protected salary difference (2008→2015) | D2 | Logic | ✅* | engine |
| R17 | Promotion durations (**9 rows**) | D1 | Data | ✅ | Promotion Rule |
| R18 | Promotion conditions (7, all required) | D1 | Workflow | ✅ | Promotion workflow |
| R19 | Post-promotion stage rule (equal / between→higher / below→first) | D1 | Logic | ✅ | engine |
| R20 | Pension: 36-mo avg, accrual 2.5%, ÷12, **Art. 21** | D3 | Logic + constants | ✅ | Pension Rule |
| R21 | Pension 100% cap of last functional salary | D3 | Logic | ✅ | engine |
| R22 | Certificate allowance **pension** (5/10/15/20%) | D3 | Data | ✅ | Allowance Rule (context=Pension) |
| R23 | Cost-of-living top-up (4 methods, default min 500,000) | D3 | Data+Logic | ⚠️ PC-9 | Rule Set Param |
| R24 | End-of-service bonus (≥30y → last full ×12) | D3 | Logic+cfg | ⚠️ PC-11 | Pension Rule |
| R25 | Income tax brackets (**4 rows**, annual, progressive) Art. 13 | D4/D3 | Data | ✅ | Income Tax Bracket |
| R26 | Tax legal allowances Art. 12 (single/married/children) | D4 | Data | ⚠️ PC-7 | Tax Allowance Rule |
| R27 | Life-insurance tax deduction (250k/500k caps) | D4 | Data | ⚠️ PC-8 | Tax Allowance Rule |
| R28 | Pension contribution rate (active deduction) | D2 | Data | ⚠️ PC-6 | Rule Set Param |
| R29 | Absence / penalty / loan / stamp deductions | D2 | Data+Logic | ⚠️ PC-13/14 | Allowance Rule (Deduction) |
| R30 | Cross-cutting: law by period date · % on Basic only · audit every calc · block on violation | D2 | Logic | ✅ | engine (all) |

**Ready now:** R1, R3–R5, R7, R8, R10, R15–R22, R25, R30. **Run provisionally + flag:** R2, R6, R9, R11–R14, R23, R24, R26–R29.

---

## 2. Fixture list

`backend/.../iraqi_government_payroll/fixtures/`, exported via `hooks.py`. All rule fixtures seed under one rule set **`IRAQ-2015 v1`**.

| Fixture file | Seeds DocType | Rows | Status |
|---|---|---|---|
| `government_rule_set.json` | Government Rule Set | 2 (2015 active, 2008 archived) | 2008 empty (PC-1) |
| `government_salary_scale.json` | Government Salary Scale (+143 detail) | 1 / 143 | ✅ |
| `qualification_appointment_rule.json` | Qualification Appointment Rule | 16 | ✅ |
| `allowance_rule.json` | Allowance Rule (cert active 7, cert pension 5, position 5, risk, craft, spouse, child, overtime, deductions 6) | ~28 | PC rows `confirmed=false` |
| `income_tax_bracket.json` | Income Tax Bracket | 4 | ✅ |
| `tax_allowance_rule.json` | Tax Allowance Rule | ~3 | ⚠️ PC-7/8 placeholder |
| `pension_rule.json` | Pension Rule | 1 | ✅ core; PC-11 field |
| `promotion_rule.json` | Promotion Rule | 9 + policy | ✅ |
| `annual_increment_rule.json` | Annual Increment Rule | 1 (12-mo eligibility) | ✅ |
| `geographic_area.json` | Geographic Area | 0 | ⚠️ PC-2 empty |
| `government_entity.json` | Government Entity | sample org tree | seed |
| `government_position.json` | Government Position | sample positions | seed |
| `role.json` | Role | 6 | ✅ exists |

Operational `Government Payroll Settings` (Single) holds engine toggles only; legal knobs (PC-3/5/6/9/10/12) live in `Rule Set Parameter`.

---

## 3. Monthly payroll calculation flow

Backend-only (Python). Service owner in parentheses.

```
0. CONTEXT            (payroll_engine)
   load Employee Payroll Profile → period_date
   resolve Government Rule Set where effective_from ≤ period_date < effective_to   [R30]

1. BASIC SALARY       (payroll_engine.scale)
   basic = Salary Scale Detail[rule_set, grade, stage]                      [R1,R3]

2. ALLOWANCES         (allowance)
   2a percentage-on-Basic: certificate_active, position, risk, craft        [R7-R10,R30]
   2b apply 200% cap to capped subset (+geographic if PC-5) → AllowedCapped [R15]
        cap violation → flag, block submit
   2c non-capped: spouse, children(min 4), geographic, cabinet, overtime,
        protected_difference                                                [R11-R14,R16]
   2d GROSS = basic + AllowedCapped + NonCapped

3. TAXABLE INCOME     (tax)
   annual = GROSS × 12
   taxable = annual − legal_allowances(Art.12) − life_insurance            [R26,R27]
   OPEN: does pension contribution reduce taxable? (confirm — see §7)

4. PENSION DEDUCTION  (pension)
   pension_ded = basic × contribution_rate                                  [R28 / PC-6]

5. INCOME TAX         (tax)
   annual_tax = Σ progressive brackets(taxable); monthly_tax = annual_tax ÷ 12   [R25]

6. OTHER DEDUCTIONS   (allowance/deduction)
   absence + penalty + loans + stamps/other                                 [R29]

7. NET SALARY         (payroll_engine)
   net = GROSS − (pension_ded + monthly_tax + other)

8. SNAPSHOT           (audit)
   write Payroll Calculation Snapshot + lines (amount, basis, rate, reason,
   source_rule, cap_applied) + rule_set + engine_version + input/output JSON  [R30]
   validation gate: missing rule / cap breach / missing field → Error before submit
```

Pension flow (Pension Calculation doc) reuses the pension service: 36-mo avg → ×2.5%×months÷12 → min(initial, last salary) → +cert pension % → +cost-of-living → −tax → net; EOS if ≥30y.

---

## 4. DocType list (revised)

| Group | DocType | vs Phase 1 |
|---|---|---|
| Org | Government Entity *(tree, NestedSet)* | NEW |
| Org | Government Position | NEW |
| Versioning spine | Government Rule Set | renamed/evolved from Government Salary Law |
| Rule member | Rule Set Parameter *(child)* | NEW |
| Rule member | Government Salary Scale + Scale Detail *(child)* | keep; `salary_law`→`rule_set` |
| Rule member | Qualification Appointment Rule | keep; `salary_law`→`rule_set` |
| Rule member | Allowance Rule | keep; add `rule_set`, `match_key`/`match_value` |
| Rule member | Income Tax Bracket | NEW |
| Rule member | Tax Allowance Rule | NEW |
| Rule member | Pension Rule | NEW |
| Rule member | Promotion Rule | NEW |
| Rule member | Annual Increment Rule | NEW |
| Rule member | Geographic Area | NEW |
| Employee | Government Employee Payroll Profile | keep; add `government_entity`, `government_position`, `rule_set` |
| Employee | Employee Monthly Salary | NEW (36-mo pension averaging) |
| Transaction | Annual Increment Request | keep; `rule_set` + snapshot link |
| Transaction | Promotion Request | keep; `rule_set` + snapshot link |
| Transaction | Pension Calculation | keep; method/service-months fields |
| Operational | Payroll Period | NEW |
| Operational | Payroll Run | NEW |
| Operational | Salary Slip + Salary Slip Line *(child)* | NEW |
| Audit/repro | Payroll Calculation Snapshot + Snapshot Line *(child)* | renamed/evolved from Salary Calculation Log |
| Settings | Government Payroll Settings *(Single)* | NEW (operational only) |

**Task #4 decision:** Income Tax Bracket, Pension Rule, Promotion Rule, Annual Increment Rule stay **separate DocTypes**, each a **member of a versioned Government Rule Set** (governed-by, not merged-into).

---

## 5. Recommended file changes

**Rename in place (M1, first task):** `government_salary_law/` → `government_rule_set/` (+ class `GovernmentRuleSet`); `salary_calculation_log/` → `payroll_calculation_snapshot/` (+ class, + fields). Update `salary_law` → `rule_set` links in Salary Scale, Qualification Appointment Rule, Allowance Rule, Employee Payroll Profile. Update frontend `types`/`api`/nav (`salary-laws`→`rule-sets`).

**Add — new DocType folders:** `government_entity`, `government_position`, `rule_set_parameter` (child), `income_tax_bracket`, `tax_allowance_rule`, `pension_rule`, `promotion_rule`, `annual_increment_rule`, `geographic_area`, `employee_monthly_salary`, `payroll_period`, `payroll_run`, `salary_slip` + `salary_slip_line` (child), `payroll_calculation_snapshot_line` (child).

**Modify — Phase 1 DocType JSONs (field additions):**
- `government_salary_scale_detail` → add `grade_code` (Data) for senior grades.
- `government_employee_payroll_profile` → `government_entity`, `government_position`, `rule_set`, `grade_code`, `spouse_eligible`, `craft_applicable`/`craft_percentage`, `total_service_months`, `bank_account`, `employment_type`.
- `allowance_rule` → `rule_set`, `match_key` (Qualification/Position/Job Category), `match_value`.
- `annual_increment_request` / `promotion_request` → `rule_set`, `effective_date`, `protected_difference` (promotion), snapshot link.
- `pension_calculation` → `cost_of_living_method`, `service_months`, `minimum_salary`, Employee Monthly Salary source link.

**Implement — services** (replace `NotImplementedError`): `payroll_engine/engine.py` (+`scale.py`), `allowance_service.py`, `tax_service.py`, `pension_service.py`, `increment_service.py`, `promotion_service.py`, `audit_service.py`.

**Add:** `fixtures/*.json` (§2), `patches/` seeders, `tests/`, update `hooks.py` (`fixtures` export + `doc_events` apply-on-submit + scheduler for due-date flags).

---

## 6. Phase 2 milestones

| M | Milestone | Deliverable | Acceptance | PC dependency |
|---|---|---|---|---|
| **M1** | Data model + renames | Renames in place; Government Rule Set spine; Government Entity tree; Government Position; all new rule/operational DocTypes; Phase-1 field additions | clean `bench migrate`; static validator passes | none |
| **M2** | Fixtures & rule loading | All fixtures under `IRAQ-2015 v1`; org + position seeds; PC rows `confirmed=false` | 143 scale, 16 qual, 4 brackets, 9 promo loaded | empty placeholders PC-1/2 |
| **M3** | Core active-salary engine | scale lookup + allowances + 200% cap + gross | cert 296,000×45% = **133,200**; appointment salaries match | R6,R9,R11–R14 provisional |
| **M4** | Tax + pension engines | brackets + Art. 21 pension | tax monthly **177,406**; pension net **1,049,744**; EOS **12,360,000** | PC-6/7/8/9/11 provisional |
| **M5** | Increment + promotion | compute + apply-to-profile + workflows | new-stage rule (equal/between→higher/below→first) verified | — |
| **M6** | Monthly payroll run | Payroll Period/Run → Salary Slip + Payroll Calculation Snapshot (rule_set + engine_version) + validation gates | batch writes slip + immutable snapshot; cap breach blocks submit | — |
| **M7** | API + frontend wiring | list/detail/forms over REST + calc triggers; RTL/Cairo display | slip renders, English numerals, zero frontend math | — |
| **M8** | Hardening | permission/validation integration tests; cap-violation report; reproducibility test (re-run snapshot → identical); clone-and-amend rule-set test; PC-confirmation pass; retroactive recalc | full suite green; PC items flipped via data only | confirm all PC-x |

**Acceptance anchors (must reproduce exactly):** certificate 133,200 · monthly tax 177,406 (taxable 14,725,800 → annual 2,128,870) · pension net 1,049,744 (avg 1,010,000, 432 months, capped 909,000, +cert 90,900, +COL 227,250) · EOS 12,360,000.

---

## 7. Open questions to resolve at M3–M4
1. **Pension contribution vs tax base** — does the active-salary pension deduction reduce taxable income (pre-tax), or is tax on full gross? Sources are silent. Affects steps 3↔4.
2. **PC-x numbers** — which official values can be supplied now so M3/M4 run on real data instead of provisional flags.
