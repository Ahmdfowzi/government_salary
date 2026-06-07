# Phase 3 — Governance, Lifecycle & Operations

> **Status: complete (M1–M8).** Built **on top of** the Phase 2 calculation
> engines without changing any salary/tax/pension math. Adds the operational
> layer that turns the engines into a governed, auditable payroll system: an
> approval workflow, employee lifecycle, immutable history, role-based authority,
> a tamper-evident audit log, a REST surface and a frontend UI.

> **M-number namespace:** Phase 3 milestones (governance) reuse the `M` prefix
> independently of the Phase 2 **engine** milestones documented in
> `ENGINE-BOUNDARIES.md` (where M3 = Active Salary … M7 = Payroll Run batch).
> "M3" below means *payroll locking*, not the active-salary engine.

---

## Milestones

| M | Title | Core change |
|---|-------|-------------|
| **M1** | Payroll Run governance workflow | Pure state machine in `services/payroll_engine/governance.py`: Draft → Calculated → Under Review → Approved → Submitted → Locked (+ Cancelled pre-submit). Whitelisted controller methods (`calculate_run` … `submit_run`) stamp audit fields. |
| **M2** | Employee lifecycle management | `services/lifecycle/`: appoint / transfer / leave-without-salary / return / retire / terminate. Each event is a permanent immutable record; payroll selects only `employment_status = Active`. |
| **M3** | Payroll locking & historical integrity | Added `Locked` state; lock from Submitted, unlock from Locked (Administrator only). `services/historical/` reconstructs past payroll from immutable snapshots + lifecycle timeline; retroactive changes into a locked period are blocked. |
| **M3.1** | Block deletion of locked runs | `Payroll Run.on_trash` explicitly aborts deletion when Submitted / Locked / `docstatus == 1`. |
| **M4** | Segregation-of-duties RBAC | `REQUIRED_ROLES` matrix + `ensure_role_allowed`: Officer prepares; Manager approves/submits/cancels; Administrator locks/unlocks; System Manager bypasses. Enforced server-side on every transition. |
| **M5** | Immutable governance audit log | New immutable `Payroll Run Governance Event` DocType; one append-only event per transition (action, from→to, actor, timestamp). Insert failure aborts the transition — no state change without its audit event. |
| **M5.1** | Smoke-harness hardening | Smoke checks moved to importable `smoke/checks.py`, run via `bench execute` (one process) so they fail hard and cannot print a false `PASSED`. |
| **M5.2** | Pin Docker Python | Bench virtualenv pinned to **Python 3.12.12** (`docker/install-app.sh`); the image default 3.14 is unsupported by Frappe v15. |
| **M5.3** | Fix `is_locked` shadowing | The controller method `is_locked()` shadowed Frappe's `Document.is_locked` **property**, breaking `check_if_locked()` on every save. Renamed to `is_run_locked()`. |
| **M6** | Governance REST API | `api/payroll_api.py`: `run_governance_action(run, action)` (thin routing over the controller) and `get_run_governance(run)` (state + `allowed_actions` + audit + event trail). Pure `governance.available_actions(state, roles)`. |
| **M7** | Payroll Runs governance UI | Frontend routes `/government-payroll/payroll-runs` (list) + `/[name]` (detail). Action buttons rendered **only** from backend `allowed_actions`; re-fetch after every action (no local workflow state); color-coded state badges; read-only audit + event timeline. |
| **M8** | Payroll Run creation | Thin validated `create_payroll_run(period, rule_set, scope, scope_reference)` + a frontend create form. Rejects a duplicate active (non-Cancelled) run for the same period + rule_set + scope + scope_reference. |

---

## What stays where (no duplication)

- **State machine, role matrix, transitions, audit writes** live in the backend
  (`governance.py` + the Payroll Run controller). The frontend and the API
  endpoints **route only** — they never re-encode workflow or authorization.
- **`allowed_actions`** (M6) is the single source the UI renders buttons from; the
  controller re-checks role and writes the audit event on every call (M4/M5).
- **History is immutable**: past payroll is reconstructed from `Payroll
  Calculation Snapshot` + the lifecycle timeline; the governance event log and the
  lifecycle records block edit/delete at the application layer.

---

## Lessons (carried forward)

1. **Never name a controller method the same as a Frappe `Document`
   property/method** (`is_locked`, `is_new`, …). It silently shadows framework
   behavior; fake-frappe unit tests do not catch it — only a live bench does
   (see M5.3).
2. **Run Frappe v15 on Python 3.10–3.12, not 3.14.** The unsupported interpreter
   surfaced a `file_lock` failure in the document-save path (see M5.2).
3. **Smoke checks must fail hard.** Drive them with `bench execute`, never
   line-by-line `bench console < script` (see M5.1).

---

## Verification (Phase 3, current)

- **164 backend unit/integration tests** pass (`python3 -m unittest`, no bench).
- **Live Docker bench** (`docker/`): `bench migrate` clean; **34** Government
  Payroll DocTypes; fixtures 143 / 16 / 4 / 9 / 6.
- **Four live smoke checks** all exit 0 (`bench execute … smoke.checks.<name>`):
  `governance`, `locking`, `api`, `create`.
- **Frontend**: `next build` + `next lint` pass.
