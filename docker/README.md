# Docker-based Frappe bench (isolated) — Iraqi Government Payroll

Run the app in a throwaway Frappe bench inside Docker. **Nothing is installed on
the macOS host** (no MariaDB/Redis/bench) — everything lives in containers and
named volumes.

Approach: the official `frappe/bench` image + `mariadb` + `redis` via Compose,
with this app **bind-mounted** at `/mnt/iraqi_government_payroll` and the helper
scripts at `/mnt/scripts`.

## 0. Prerequisite
Start the Docker daemon (Docker Desktop). Verify:
```bash
docker info >/dev/null && echo "docker daemon OK"
```
> On this machine the Docker CLI is installed but the **daemon was not running** —
> start Docker Desktop first.

## 1. Bring up the containers
From the project root:
```bash
docker compose -f docker/docker-compose.yml up -d
```
First run pulls images (`frappe/bench`, `mariadb:10.6`, `redis:6.2-alpine`) and
starts MariaDB (with a healthcheck), two Redis instances, and the `frappe` container.

## 2. Init bench, create site, install this app, migrate
One command (runs the helper inside the container):
```bash
docker compose -f docker/docker-compose.yml exec frappe bash /mnt/scripts/install-app.sh
```
This performs (idempotently):
- `bench init --frappe-branch version-15`
- points bench at the `mariadb` / `redis-cache` / `redis-queue` services
- `bench new-site payroll.localhost` (db root pwd `123`, admin pwd `admin`)
- `bench get-app /mnt/iraqi_government_payroll`
- `bench --site payroll.localhost install-app iraqi_government_payroll`
- `bench --site payroll.localhost migrate`
- prints fixture counts (expect: scale **143** · qual **16** · brackets **4** · durations **9** · roles **6** · DocTypes **34**)

## 3. Salary Slip + Payroll Run smoke test
```bash
docker compose -f docker/docker-compose.yml exec frappe \
  bash -lc "cd ~/frappe-bench && bench --site payroll.localhost console < /mnt/scripts/smoke-test.py"
```
Expected: `basic 296000 · gross 429200 · net 371487`, Payroll Run
`Completed With Warnings`, then `SMOKE TEST PASSED`.

## 3b. Phase 3 governance smoke checks
Run these via **`bench execute`** (a single process), NOT `bench console`. With
`bench execute` the first failed assertion raises, the command exits non-zero,
and the trailing `… PASSED` line is unreachable unless every check passed — so a
failure can never be masked by a false PASSED (the old line-by-line `bench
console < script` harness could both swallow errors and print a false PASSED).

Four checks live in `iraqi_government_payroll.smoke.checks` —
`governance` · `locking` · `api` · `create`:
```bash
for c in governance locking api create; do
  docker compose -f docker/docker-compose.yml exec frappe \
    bash -lc "cd ~/frappe-bench && bench --site payroll.localhost execute \
      iraqi_government_payroll.smoke.checks.$c"
done
```
Expected: each prints its per-step trace ending in `… SMOKE TEST PASSED` and exits
`0` — `GOVERNANCE`, `PAYROLL LOCKING`, `GOVERNANCE API`, `PAYROLL RUN CREATE`.
`docker/smoke-*.py` are thin entry points to the same functions.

> **Python pin:** `install-app.sh` forces the bench virtualenv onto **Python
> 3.12.12** (the `frappe/bench` image defaults to 3.14, which Frappe v15 does not
> support and which breaks the document-save lock path). It self-heals an existing
> bench's env without touching the site/DB.

## 4. (Optional) open the desk UI
```bash
docker compose -f docker/docker-compose.yml exec frappe \
  bash -lc "cd ~/frappe-bench && bench --site payroll.localhost serve --port 8000 --host 0.0.0.0"
# browse http://payroll.localhost:8000  (add '127.0.0.1 payroll.localhost' to /etc/hosts) — login Administrator / admin
```

## 5. Tear down
```bash
docker compose -f docker/docker-compose.yml down          # stop (keep data volumes)
docker compose -f docker/docker-compose.yml down -v       # stop + delete all data volumes
```

## Notes
- DB root password (`123`) and admin password (`admin`) are for the disposable
  local container only — do not reuse in production.
- `version-15` matches the app's DocType/feature set; `Currency` is a Frappe
  framework DocType so ERPNext is not required.
- If `migrate` reports a Select/Link error, see the troubleshooting table in
  `../BENCH-READINESS.md`.
