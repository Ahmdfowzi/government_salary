# Production Readiness Audit — Iraqi Government Payroll

Brutally honest assessment of whether the system is ready for **real-world
deployment** — not just whether the code works. The application logic and data model
are strong and thoroughly validated (290 host tests + 20 smoke checks, full UAT pass,
immutable snapshots, RBAC, audit trail). The **operating environment** (deployment,
security hardening, scale, backup, monitoring) is **not** production-ready: this runs
on a disposable dev Docker bench.

> **Production readiness score: 61 / 100**
> **Recommendation: NO-GO** for production as-is. Conditional GO for a small, isolated
> pilot (< 1,000 employees) only after the two Critical items are fixed.

The score is deliberately not inflated — the app is functionally excellent (the hard
part), but several deployment/ops/security/scale gaps are real blockers for handling
real citizens' payroll and PII.

---

## Category scores
| # | Category | Score | One-line verdict |
|---|---|---|---|
| 1 | Security | 65 | App-level strong (no guest API, RBAC, immutable audit); **dev creds + no TLS** |
| 2 | Database | 75 | Good integrity + duplicate guards; **indexes added this audit** |
| 3 | Operational | 45 | Backup/DR now documented (not automated); no auto-start/restart |
| 4 | Performance | 55 | OK to ~1k synchronous; **10k–50k times out** (needs async) |
| 5 | Reporting | 90 | PDF/Excel/CSV/Arabic/snapshot all tested ✓ |
| 6 | Data Governance | 95 | Lock/snapshot/audit/promotion/increment/pension immutable ✓ |
| 7 | Deployment | 35 | Dev-grade Docker only; no prod config / frontend deploy |
| 8 | Monitoring | 25 | No app logging/error-tracking/alerting beyond Frappe defaults |
| | **Overall** | **61** | Built & validated; **operating environment not production-ready** |

---

## 1. Security — 65
**Good (verified):** no `allow_guest` endpoints (every API requires login); RBAC enforced
by DocType permissions + the governance role gate (tested); the accounting-journal export
is gated; **Payroll Calculation Snapshot is immutable** (`on_update`/`on_trash` throw);
locked runs reject recalculation/delete; the audit trail (Payroll Run Governance Event)
is append-only and tested; payroll math is pure Python (no string-built SQL).
**Risks:** default credentials (Administrator/`admin`, DB root/`123`); no TLS/HTTPS
(auth + payroll PII travel in plaintext); secrets live in the compose `environment`; no
documented rate-limiting / brute-force policy on login.

## 2. Database — 75
**Good:** `employee_number` unique; naming-series uniqueness; duplicate-run guard; idempotent
slip upsert; immutable snapshots; app-level referential integrity (Frappe Link validation
on save). **Fixed this audit:** added `search_index` on the hot Link/filter fields
(`Salary Slip.payroll_run/employee_profile/payroll_period`, `Payroll Calculation Snapshot.
salary_slip/employee_profile/payroll_period/calculation_type`, `Governance Event.payroll_run`,
`Pension Calculation.employee_profile/period_date`) and migrated — report/snapshot queries no
longer full-scan at scale. **Residual:** no DB-level foreign keys (Frappe is app-level); no
partitioning/archival plan for very large snapshot tables.

## 3. Operational — 45
**Fixed/added this audit:** `docker/README` now documents **backup/restore/DR**
(`bench backup --with-files` + restore) and a **production-hardening checklist**; restoring a
backup reproduces immutable snapshots bit-for-bit. **Risks:** backups are not automated/
scheduled or restore-drilled; the `frappe` container runs `sleep infinity` — the web server,
background workers and scheduler are **not auto-started**, and there is no `restart:` policy
or healthcheck on it; migration is documented (patches + `bench migrate`).

## 4. Performance — 55
Measured on the live bench: **7.8 ms/employee** synchronous.
| Employees | Est. payroll-run time | Verdict |
|---|---|---|
| 1,000 | ~8 s | OK (synchronous) |
| 10,000 | ~78 s | **Exceeds typical gunicorn timeout (120 s margin thin)** |
| 50,000 | ~391 s (~6.5 min) | **Will time out** as a synchronous HTTP request |
`calculate_run` is a **synchronous** whitelisted method, and the batch does per-employee
`get_doc`/`insert`/`save` (each slip recomputes on save — an N+1). For ≥ 10k employees this
must run as a **background job** (`frappe.enqueue`) with progress polling, and ideally bulk
slip insertion. Report queries are now indexed (§2).

## 5. Reporting — 90
PDF (wkhtmltopdf + embedded Cairo), Excel (openpyxl), CSV, Arabic RTL rendering, and snapshot
consistency are all implemented and tested (`reports`, `bank_transfer`, `excel_export`,
`pdf_export`, `accounting_journal`, `pension_report` smokes). Locked-run reports read the
immutable snapshot via `reports_api._rows_for`. Minor: very large exports are built in-memory
(fine to a few thousand rows; stream for tens of thousands).

## 6. Data Governance — 95
Strongest area. Payroll lock integrity, snapshot immutability, append-only audit history,
and promotion/increment/pension history are all enforced and test-covered (`test_locking`,
`test_governance_log`, `test_hardening`, `uat_demo_cycle`). Historical payroll is reproducible
and cannot be altered after lock.

## 7. Deployment — 35
The Docker setup is an explicitly **disposable dev bench**: no nginx/TLS, no gunicorn tuning,
no auto-start of web/workers/scheduler, no healthcheck/restart policy, dev passwords. The
**frontend has no production deployment** path (only `next start` / the dev proxy is
documented — no container/systemd/PM2, no `NEXT_PUBLIC_*` prod config, no CDN/static hosting).
A real deployment needs: reverse proxy + TLS, process supervision, separate frontend hosting,
and the bench web server + workers auto-started.

## 8. Monitoring — 25
Weakest area. No application logging shipped out, no error tracking (Sentry-style), no
alerting. Failed payroll runs are visible (`run_status = Failed`, `error_log` on the run) but
nobody is notified. No health/uptime checks. Needs: centralized logs, error tracking, and an
alert on a `Failed` run or a stuck `Processing` run.

---

## Risks by severity

### Critical (block production)
- **C1 — Default/dev credentials.** Administrator/`admin` and DB root/`123`. Anyone who
  reaches the host can read/modify all payroll. *Fix:* set strong unique passwords; rotate;
  move to a secret store.
- **C2 — No TLS/HTTPS.** Login and payroll PII are transmitted in plaintext. *Fix:* terminate
  TLS at nginx in front of Frappe and the frontend.

### High
- **H1 — Synchronous payroll runs time out at scale.** ≥ 10k employees exceed the HTTP
  timeout. *Fix:* run `calculate_run` via `frappe.enqueue` (background job) + progress polling.
- **H2 — No automated/verified backups.** Manual procedure now documented but not scheduled or
  restore-drilled. *Fix:* nightly `bench backup --with-files`, offsite copy, monthly restore test.
- **H3 — No monitoring/alerting.** *Fix:* ship logs, add error tracking, alert on failed runs.
- **H4 — Services not auto-started / no restart policy / no healthcheck.** A container restart
  leaves the system down. *Fix:* supervise web + workers + scheduler; add `restart: unless-stopped`
  and a healthcheck.

### Medium
- **M1 — N+1 per-employee insert/save** in the payroll batch (7.8 ms/emp). *Fix:* bulk insert slips.
- **M2 — No frontend production deployment** path. *Fix:* containerize/host the Next app with prod env.
- **M3 — Secrets in compose `environment`.** *Fix:* env files / secret store.
- **M4 — No documented login rate-limiting / brute-force policy.**

### Low
- **L1 — Index coverage on hot Link fields.** *Fixed this audit* (search_index + migrate).
- **L2 — No DB-level foreign keys** (app-level Link validation only) — acceptable for Frappe.
- **L3 — Leftover demo/test records** (`FW-EMPTY` entity, `UAT-*` personas) in the dev bench —
  cosmetic; clean before a production data load.

---

## Recommended fixes (priority order)
1. **C1/C2:** strong credentials + TLS behind nginx — *before any real data*.
2. **H1:** make large payroll runs asynchronous (`frappe.enqueue`).
3. **H2:** automate + verify backups (DR drill).
4. **H4:** supervise & auto-start services; add restart policy + healthcheck.
5. **H3:** logging + error tracking + failed-run alerting.
6. **M1–M4:** bulk slip insert; frontend prod hosting; secret store; login throttling.

## Fixes implemented in this audit (no business logic changed)
- Added `search_index` on the hot Link/filter fields and migrated (report/snapshot queries
  no longer full-scan); 290 host tests + smoke remain green.
- Documented **backup/restore/DR** and a **production-hardening checklist** in `docker/README`.

## Test/build status at audit time
- 290 host unit tests ✓ · 20 smoke checks ✓ · frontend lint + build ✓ (23 routes).

## Go / No-Go
**NO-GO** for production as-is. The application is functionally production-grade and
exhaustively validated, but the deployment, security hardening, scalability (async runs),
backup automation and monitoring are not in place. **Conditional GO** for a controlled pilot
(< 1,000 employees, isolated network, manual nightly backups) **only after C1 and C2** are
addressed. Re-audit after the High items are done to lift the score toward production.
