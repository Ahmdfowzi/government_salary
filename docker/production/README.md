# Production deployment — Iraqi Government Payroll

This folder turns the disposable dev bench (`docker/docker-compose.yml`) into a
hardened deployment that addresses the blockers in
[`../../PRODUCTION-READINESS-AUDIT.md`](../../PRODUCTION-READINESS-AUDIT.md):
credentials/secrets, TLS, async payroll runs, automated backups, auto-start +
healthchecks, and monitoring/alerting.

> Treat the compose file and nginx config as **templates**. Review image tags, the
> frontend build, and certificate paths for your environment.

## Files
| File | Purpose |
|---|---|
| `.env.production.example` | Required env vars (copy to `.env.production`, fill real secrets) |
| `docker-compose.prod.yml` | Prod override: restart, healthchecks, auto-start, nginx, frontend, certbot |
| `nginx.conf` | TLS reverse proxy (HTTPS, security headers, same-origin routing) |
| `start-production.sh` | Container entrypoint — auto-starts web + workers + scheduler |
| `backup.sh` | Nightly DB + public/private-files backup, with integrity check + retention |
| `restore.sh` | Restore from a backup set |
| `backup-verify.sh` | **DR drill** — restores into a throwaway site and verifies |
| `go-live-check.sh` | **Blocks go-live** while default creds / dev settings remain |

## 1. Credentials & secrets (Critical C1)
```bash
cp docker/production/.env.production.example docker/production/.env.production
# edit .env.production — generate secrets with: openssl rand -base64 32
```
- `.env.production` is git-ignored; the committed `*.example` holds only placeholders.
- The MariaDB root password and the Frappe Administrator password **must not** be the
  dev defaults (`123` / `admin`). Rotate the Administrator password after first login:
  `bench --site $SITE set-admin-password '<new>'`.
- `go-live-check.sh` fails the deploy if either default is still in place.

## 2. TLS / HTTPS (Critical C2)
1. Point your DNS A record at the host and set `server_name` + cert paths in `nginx.conf`.
2. Bring the stack up (nginx answers `:80` for the ACME challenge).
3. Issue the certificate once:
   ```bash
   docker compose -f docker/docker-compose.yml -f docker/production/docker-compose.prod.yml \
     run --rm certbot certonly --webroot -w /var/www/certbot \
     -d payroll.example.gov.iq --email "$CERTBOT_EMAIL" --agree-tos --no-eff-email
   docker compose ... restart nginx
   ```
   The `certbot` service then auto-renews every 12h.
- **Secure cookies / sessions:** with HTTPS + HSTS, enable secure session cookies so the
  Frappe `sid` cookie is never sent over plaintext:
  `bench --site $SITE set-config -g cookie_secure 1` and keep
  the default HttpOnly session cookie. Sessions are server-side (Redis); a logout/idle
  timeout can be tightened via `session_expiry`.
- **CORS / proxy assumptions:** the frontend and backend are served from the **same
  origin** through nginx (the Next app proxies `/api` to Frappe). No cross-origin
  requests are made, so no CORS allow-list is required. Frappe sets
  `X-Forwarded-Proto https` from nginx, so it generates `https://` URLs.

## 3. Async payroll runs (High H1)
Large runs are calculated by a **background worker** (`frappe.enqueue`) so they never
hit the HTTP/gunicorn timeout. `start-production.sh` auto-starts the workers + scheduler;
the UI enqueues via `enqueue_calculation` and polls `calculation_status`. The synchronous
`calculate_run` remains for small/programmatic runs. (Backend: `calculate_run_async`,
`jobs.run_calculation_job`; smoke: `async_payroll_run`.)

## 4. Backups & DR (High H2)
- **Schedule** (host cron, nightly):
  ```cron
  0 1 * * * docker compose -f docker/docker-compose.yml -f docker/production/docker-compose.prod.yml \
              exec -T frappe bash /mnt/scripts/production/backup.sh >> /var/log/payroll-backup.log 2>&1
  ```
- Backups land in the `backups-data` volume (`/backups`); **replicate off-site**.
- **Retention:** `BACKUP_RETENTION_DAYS` (default 30). Keep ≥ 30 days; consider weekly
  archives kept ≥ 1 year for audit.
- **Verify monthly** with the DR drill — restores into a throwaway site and queries it:
  ```bash
  docker compose ... exec frappe bash /mnt/scripts/production/backup-verify.sh /backups
  ```
- Restoring reproduces the immutable snapshots exactly, so locked payroll history is
  recoverable bit-for-bit.

## 5. Auto-start & healthchecks (High H4)
The override sets `restart: unless-stopped` on every service and healthchecks on
MariaDB, Redis and Frappe (`/api/method/ping`). `start-production.sh` replaces the dev
`sleep infinity`, launching gunicorn (foreground) + workers + scheduler, so the stack
recovers from reboots and crashes automatically.

## 6. Monitoring & alerting (High H3)
The app already records failures (`Payroll Run.run_status = Failed`, `error_log`; async
failures are written to the Frappe **Error Log** via `frappe.log_error`). To make them
visible:
- **Structured logs:** ship `frappe-bench/logs/*.log` (web, worker, scheduler) to your log
  stack (Loki/ELK/CloudWatch). Run gunicorn with access logs; nginx access/error logs too.
- **Error tracking:** set `SENTRY_DSN` (Frappe supports Sentry) to capture exceptions and
  failed background jobs.
- **Uptime/health:** point Uptime Kuma (or your monitor) at `https://<host>/api/method/ping`.
- **Metrics:** export host/container metrics (Prometheus node-exporter + cAdvisor) and
  MariaDB/Redis exporters; alert on the rules below.

**Alert triggers (wire these):**
| Trigger | Signal |
|---|---|
| Failed payroll run | `Payroll Run.run_status = Failed` (notification / webhook) or a new Error Log titled `Payroll async run failed` |
| Backup failure | `backup.sh` non-zero exit (cron MAILTO / alert webhook) |
| Worker down | RQ queue depth rising / no jobs processed; `bench doctor` |
| Disk usage high | node-exporter filesystem ≥ 85% |
| Database unavailable | MariaDB healthcheck failing / connection errors in logs |

## 7. Go-live gate
Run the blocker check before serving real data (fails the deploy on any blocker):
```bash
docker compose -f docker/docker-compose.yml -f docker/production/docker-compose.prod.yml \
  exec frappe bash /mnt/scripts/production/go-live-check.sh
```
Checks: non-default DB root password, Administrator password rotated off `admin`,
`developer_mode` off, scheduler enabled, encryption key set.
