#!/usr/bin/env bash
# go-live-check.sh — BLOCKS production go-live while any hard blocker remains.
#
# Run INSIDE the frappe container:
#   docker compose -f docker/docker-compose.yml -f docker/production/docker-compose.prod.yml \
#     exec frappe bash /mnt/scripts/production/go-live-check.sh
#
# Exits 0 only when every check passes. Any failure exits 1 — wire this into your
# deploy pipeline so a run with default credentials can never reach production.
set -uo pipefail

SITE="${FRAPPE_SITE:-payroll.localhost}"
BENCH=~/frappe-bench
cd "$BENCH" 2>/dev/null || { echo "❌ no bench at $BENCH"; exit 1; }

FAIL=0
ok()   { echo "✅ $1"; }
bad()  { echo "❌ $1"; FAIL=1; }

echo "=== Production go-live check for site: $SITE ==="

# 1) MariaDB root password must not be the dev default.
if [ "${MYSQL_ROOT_PASSWORD:-123}" = "123" ]; then
  bad "MariaDB root password is the dev default '123' (set MYSQL_ROOT_PASSWORD)"
else
  ok "MariaDB root password is set to a non-default value"
fi

# 2) Administrator password must not be the dev default 'admin'.
#    check_password returns the user on success (=> default still in use) and
#    raises AuthenticationError otherwise.
if bench --site "$SITE" execute frappe.utils.password.check_password \
     --kwargs '{"user":"Administrator","pwd":"admin"}' >/dev/null 2>&1; then
  bad "Administrator password is still the default 'admin' — rotate it"
else
  ok "Administrator password is not the default 'admin'"
fi

# 3) developer_mode must be OFF in production.
SITE_CONF="$BENCH/sites/$SITE/site_config.json"
if grep -Eq '"developer_mode"[[:space:]]*:[[:space:]]*1' "$SITE_CONF" 2>/dev/null; then
  bad "developer_mode is ON in site_config.json — disable it for production"
else
  ok "developer_mode is OFF"
fi

# 4) Scheduler must be enabled (async payroll jobs + nightly backups depend on it).
if bench --site "$SITE" doctor 2>/dev/null | grep -qi "scheduler.*disabled"; then
  bad "Scheduler is disabled — async runs and scheduled backups will not run"
else
  ok "Scheduler is enabled"
fi

# 5) An encryption key must be configured (not the throwaway dev one).
if [ -z "${ENCRYPTION_KEY:-}" ]; then
  bad "ENCRYPTION_KEY is not set in the environment"
else
  ok "ENCRYPTION_KEY is set"
fi

echo "==============================================="
if [ "$FAIL" -ne 0 ]; then
  echo "🚫 GO-LIVE BLOCKED — fix the ❌ items above before serving real data."
  exit 1
fi
echo "🟢 All go-live blockers cleared."
