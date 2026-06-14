#!/usr/bin/env bash
# restore.sh — restore the payroll system of record from a backup set.
#
# Run INSIDE the frappe container, pointing at a backup directory produced by
# backup.sh (containing *-database.sql.gz and the *-files / *-private-files tars):
#
#   docker compose ... exec frappe bash /mnt/scripts/production/restore.sh /backups/20260614_010000
#
# DR note: restoring reproduces the immutable Payroll Calculation Snapshots exactly,
# so locked payroll history is recovered bit-for-bit.
set -euo pipefail

SITE="${FRAPPE_SITE:-payroll.localhost}"
BENCH=~/frappe-bench
SET_DIR="${1:?usage: restore.sh <backup-set-dir>}"

cd "$BENCH"

DB=$(ls "$SET_DIR"/*-database.sql.gz 2>/dev/null | head -1)
PUB=$(ls "$SET_DIR"/*-files.tar 2>/dev/null | grep -v private | head -1 || true)
PRIV=$(ls "$SET_DIR"/*-private-files.tar 2>/dev/null | head -1 || true)
[ -n "$DB" ] || { echo "no *-database.sql.gz in $SET_DIR"; exit 1; }

echo "[restore] DB=$DB"
echo "[restore] public=$PUB private=$PRIV"

ARGS=(--site "$SITE" restore "$DB")
[ -n "$PUB" ]  && ARGS+=(--with-public-files "$PUB")
[ -n "$PRIV" ] && ARGS+=(--with-private-files "$PRIV")

bench "${ARGS[@]}"
bench --site "$SITE" migrate
echo "[restore] done — verify with a sanity query (e.g. count Payroll Run / Locked runs)."
