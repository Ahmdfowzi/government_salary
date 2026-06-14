#!/usr/bin/env bash
# backup-verify.sh — DISASTER-RECOVERY DRILL. Proves a backup actually restores.
#
# Restores the newest backup set into a THROWAWAY temporary site, runs a sanity
# query (counts Payroll Runs + Locked runs), then drops the temp site. The live
# production site is never touched. Run INSIDE the frappe container, e.g. monthly:
#
#   docker compose ... exec frappe bash /mnt/scripts/production/backup-verify.sh /backups
#
# Exits 0 only if the restored site is queryable. Wire monthly + alert on failure.
set -euo pipefail

SITE="${FRAPPE_SITE:-payroll.localhost}"
BENCH=~/frappe-bench
DEST="${1:-${BACKUP_DEST:-/backups}}"
TMP_SITE="drill.$(date -u +%s).localhost"
ROOT_PW="${MYSQL_ROOT_PASSWORD:-123}"

cd "$BENCH"

SET_DIR=$(ls -dt "$DEST"/*/ 2>/dev/null | head -1)
[ -n "$SET_DIR" ] || { echo "no backup sets under $DEST"; exit 1; }
DB=$(ls "$SET_DIR"/*-database.sql.gz 2>/dev/null | head -1)
[ -n "$DB" ] || { echo "no database dump in $SET_DIR"; exit 1; }
echo "[drill] restoring $DB into throwaway site $TMP_SITE"

cleanup() {
  bench drop-site "$TMP_SITE" --db-root-password "$ROOT_PW" --force --no-backup >/dev/null 2>&1 || true
}
trap cleanup EXIT

bench new-site "$TMP_SITE" \
  --db-root-password "$ROOT_PW" \
  --admin-password "drill-throwaway" \
  --no-mariadb-socket >/dev/null

bench --site "$TMP_SITE" restore "$DB" --db-root-password "$ROOT_PW" >/dev/null

RUNS=$(bench --site "$TMP_SITE" execute frappe.client.get_count --kwargs '{"doctype":"Payroll Run"}' 2>/dev/null | tail -1)
LOCKED=$(bench --site "$TMP_SITE" execute frappe.client.get_count \
           --kwargs '{"doctype":"Payroll Run","filters":{"workflow_state":"Locked"}}' 2>/dev/null | tail -1)
echo "[drill] restored Payroll Runs=$RUNS  Locked=$LOCKED"

case "$RUNS" in ''|*[!0-9]*) echo "🚫 DR DRILL FAILED — restored site not queryable"; exit 1;; esac
echo "🟢 DR DRILL PASSED — backup restores and is queryable."
