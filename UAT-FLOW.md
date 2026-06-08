# UAT Flow — Iraqi Government Payroll

End-to-end User Acceptance Testing scenarios over realistic **demo data**, so the
system can be demonstrated as if used by a real government entity.

> All demo records are clearly marked: Government Entity codes and employee numbers
> are prefixed **`DEMO-`** and Arabic names are tagged **«تجريبي»**. Demo data is
> seeded on demand (never auto-loaded), so it does not affect production installs.

---

## 0. Seed the demo data (one-time, idempotent)

```bash
docker compose -f docker/docker-compose.yml exec frappe bash -lc \
  "cd ~/frappe-bench && bench --site payroll.localhost execute \
   iraqi_government_payroll.demo.seed.seed_demo"
```

Creates (idempotent — safe to re-run):

| Item | Demo content |
|---|---|
| Government structure | Ministry → Directorate → Department → **Unit** (`DEMO-MIN/DIR/DEPT/UNIT`) |
| Employees | **30** profiles (`DEMO-EMP-001…030`): mixed grades (3–10), stages (1–11), qualifications (Bachelor…Doctorate), appointment years (1990–2019 → 5–35 yrs service), ~1/7 with no bank account |
| Payroll runs (scoped to `DEMO-UNIT`) | **Active** 2024-03 (Calculated) · **Completed** 2024-02 (Submitted) · **Locked** 2024-01 (Locked, slips submitted → immutable snapshots) |
| Pension calculations | 6 retirees, varied qualifications & service years (Approved / Calculated) |
| Increment requests | 4 (Approved + pending) |
| Promotion requests | 4 (Approved + pending) |
| Account mapping | The 6 journal account codes (so the accounting export works) |

A `demo` smoke check re-runs the seed and verifies non-empty reports:
`bench --site payroll.localhost execute iraqi_government_payroll.smoke.checks.demo`.

---

## 1. Create employee
- UI: **الموظفون** → search/list the demo employees; **عرض/تعديل** opens the Frappe
  desk form (edit allowed only for HR/payroll-write roles).
- New: create a `Government Employee Payroll Profile` in the desk — set rule set
  `IRAQ-2015`, grade code, stage, qualification, government entity, bank fields.
  Basic salary is resolved by the engine (read-only).

## 2. Run payroll
- UI: **دورات الرواتب** → (manage roles) create a run: select period, rule set,
  scope (e.g. *Government Entity* = the demo unit) → **إنشاء**.
- On the run's detail page press **احتساب** → state moves Draft → **Calculated**
  and draft Salary Slips are built for the active employees.
- Advance with **إرسال للمراجعة → اعتماد → تقديم** (buttons appear only for the
  roles the backend permits; they come from `allowed_actions`).

## 3. Lock payroll
- After **Submitted**, press **قفل** (Administrator only) → state **Locked**.
- The detail page shows the locked explanation: a locked run is a final,
  immutable record; reports and the journal then read from the **Snapshot**, not
  the live slips. Recalculation/deletion are blocked; unlocking needs an admin.

## 4. Generate reports
- UI: **التقارير** → choose a run and a report:
  Run Summary · Employee Register · Allowances · Deductions · Tax · Bank Transfer ·
  (Pension via its own page). Each shows a short Arabic description and a totals row.
- Active run → live Salary Slip; Locked run → immutable Snapshot (same figures).

## 5. Export CSV
- On Reports / Pension / Accounting, press **تنزيل CSV** (hidden for Read Only
  User). Opens in Excel with Arabic headers (UTF-8 BOM).

## 6. Export Excel
- Press **تنزيل Excel** → server-generated `.xlsx` (openpyxl), RTL sheet, bold
  header + totals row.

## 7. Export PDF
- Press **تنزيل PDF** (reports & pension) → server-generated PDF (wkhtmltopdf) with
  the bundled Amiri Arabic font, RTL, landscape.

## 8. Generate bank transfer
- **التقارير → تحويل بنكي** (or the report selector): one row per employee with net
  + bank details. Rows with no IBAN/account or zero net are **flagged** (`ناقص`)
  and highlighted — never silently dropped. Export to CSV/Excel.

## 9. Generate accounting journal
- UI: **القيد المحاسبي** (Finance / payroll-admin roles only). Pick a run → a
  **balanced** debit/credit proposal is shown with a *متوازن* pill.
- Banner makes clear it is **proposal only — no GL posting**. Requires the Payroll
  Account Mapping (seeded). Export to CSV/Excel.

## 10. Review pension register
- UI: **كشف التقاعد** → filter by date range / status → 15-column register with a
  totals summary (count + gross + net). Export where the role allows.

---

## Role-aware UAT notes
- The backend is the source of truth: lock/unlock come from `allowed_actions`; the
  accounting export is gated server-side; Read Only User has no export/write.
- Suggested demo logins (assign roles in the desk): **Government Payroll
  Administrator** (full), **Payroll Manager** (approve/submit), **Payroll Officer**
  (calculate), **Finance Officer** (journal + exports), **Auditor** / **Read Only
  User** (read-only, no exports).

## Verification snapshot (against the seeded data)
- Employee/Tax registers: 30 rows; Bank transfer: 30 rows, 4 flagged incomplete.
- Locked run reports: 30 rows sourced from snapshots.
- Accounting journal: balanced (debit = credit). Pension register: 6 rows.
