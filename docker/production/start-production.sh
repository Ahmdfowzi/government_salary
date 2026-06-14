#!/usr/bin/env bash
# start-production.sh — container entrypoint that AUTO-STARTS the full Frappe
# runtime (web + background workers + scheduler) for production.
#
# Used as the `frappe` service `command` by docker-compose.prod.yml, so the stack
# comes up on `docker compose up -d` and on every container restart — replacing the
# dev `sleep infinity`. Gunicorn runs in the FOREGROUND so the container's health
# is tied to the web server (and `restart: unless-stopped` recovers a crash).
set -euo pipefail

SITE="${FRAPPE_SITE:-payroll.localhost}"
BENCH=~/frappe-bench
WORKERS="${GUNICORN_WORKERS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-300}"

cd "$BENCH"

# Point bench at the compose service hostnames (idempotent).
bench set-config -g db_host mariadb        >/dev/null 2>&1 || true
bench set-config -g redis_cache  "redis://redis-cache:6379"  >/dev/null 2>&1 || true
bench set-config -g redis_queue  "redis://redis-queue:6379"  >/dev/null 2>&1 || true
bench set-config -g redis_socketio "redis://redis-queue:6379" >/dev/null 2>&1 || true

# Enable the scheduler (async payroll jobs + scheduled backups depend on it).
bench --site "$SITE" scheduler enable >/dev/null 2>&1 || true

echo "[start-production] launching background workers (default, short, long)…"
bench worker --queue default,short,long &        # processes frappe.enqueue jobs (async payroll runs)
WORKER_PID=$!

echo "[start-production] launching scheduler…"
bench schedule &                                  # the scheduler beat (enqueues periodic jobs)
SCHED_PID=$!

# Clean shutdown of children when the container stops.
trap 'kill "$WORKER_PID" "$SCHED_PID" 2>/dev/null || true' TERM INT

echo "[start-production] launching gunicorn on :8000 (workers=$WORKERS timeout=$TIMEOUT)…"
cd "$BENCH/sites"
exec "$BENCH/env/bin/gunicorn" \
  --bind 0.0.0.0:8000 \
  --workers "$WORKERS" \
  --timeout "$TIMEOUT" \
  --preload \
  frappe.app:application
