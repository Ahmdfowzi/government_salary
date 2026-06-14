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

## 4. Start the Frappe web server (REQUIRED for the Next.js frontend)
The container's `frappe` service runs `sleep infinity` — the **web server is not
auto-started**. The Next.js frontend proxies `/api/*` to this server, so it MUST be
running or every API call returns 500 and login fails. Start it (foreground):
```bash
docker compose -f docker/docker-compose.yml exec frappe \
  bash -lc "cd ~/frappe-bench && bench --site payroll.localhost serve --port 8000 --host 0.0.0.0"
```
…or in the background so the terminal is free:
```bash
docker compose -f docker/docker-compose.yml exec -d frappe \
  bash -lc "cd ~/frappe-bench && nohup bench serve --port 8000 >/tmp/benchserve.log 2>&1 &"
```
Then browse `http://payroll.localhost:8000` (add `127.0.0.1 payroll.localhost` to
`/etc/hosts`) — login Administrator / admin. The Next frontend (`npm run dev` /
`npm run build && npm start`) proxies to it via `FRAPPE_PROXY_TARGET` (default
`http://payroll.localhost:8000`).

## 5. Tear down
```bash
docker compose -f docker/docker-compose.yml down          # stop (keep data volumes)
docker compose -f docker/docker-compose.yml down -v       # stop + delete all data volumes
```

## 6. Backup / Restore / Disaster Recovery
The DB + uploaded files are the system of record (payroll snapshots are immutable).
**Take a backup before every migrate and before every payroll lock.**
```bash
# Backup (DB + public & private files), then copy out of the container:
docker compose -f docker/docker-compose.yml exec frappe \
  bash -lc "cd ~/frappe-bench && bench --site payroll.localhost backup --with-files"
docker compose -f docker/docker-compose.yml cp \
  frappe:/home/frappe/frappe-bench/sites/payroll.localhost/private/backups ./backups

# Restore into a fresh bench/site:
docker compose -f docker/docker-compose.yml exec frappe \
  bash -lc "cd ~/frappe-bench && bench --site payroll.localhost restore <path-to-sql.gz> \
            --with-public-files <files.tar> --with-private-files <private-files.tar>"
```
- **Schedule:** nightly `bench backup --with-files` + offsite copy; retain ≥ 30 days.
  (For a real deployment, automate via cron/systemd and verify restores monthly.)
- **DR:** restoring a backup reproduces all immutable snapshots exactly, so locked
  payroll history is recoverable bit-for-bit.

## 7. Production hardening checklist (NOT done by this dev compose)
This compose is a **disposable dev bench**, not a production deployment. Before going
live, address (see `../PRODUCTION-READINESS-AUDIT.md`):
- Change the DB root + Administrator passwords; move secrets to a secret store / env file.
- Put Frappe behind nginx with **HTTPS/TLS**; run gunicorn (not `bench serve`) with a
  worker count and an increased timeout (payroll runs are long).
- Run **large payroll runs as background jobs** (`frappe.enqueue`) — a synchronous
  `calculate_run` over 10k+ employees exceeds the HTTP timeout.
- Add a `restart: unless-stopped` policy + a healthcheck to the `frappe` service, and
  auto-start the web server + background workers + scheduler.
- Add monitoring (request/error logs shipped out, Sentry-style error tracking) and
  alerting on a `Failed` payroll run.

## Notes
- DB root password (`123`) and admin password (`admin`) are for the disposable
  local container only — do not reuse in production.
- `version-15` matches the app's DocType/feature set; `Currency` is a Frappe
  framework DocType so ERPNext is not required.
- If `migrate` reports a Select/Link error, see the troubleshooting table in
  `../BENCH-READINESS.md`.
