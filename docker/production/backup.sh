#!/usr/bin/env bash
# backup.sh — automated nightly backup of the payroll system of record.
#
# Backs up: the SITE DATABASE + sites/<site>/private files + sites/<site>/public
# files (bench backup --with-files covers all three). Copies the artifacts to a
# host-mounted directory and prunes by retention. Designed to run from cron/systemd
# on the host (which invokes it inside the frappe container), e.g. nightly:
#
#   0 1 * * *  docker compose -f docker/docker-compose.yml -f docker/production/docker-compose.prod.yml \
#                exec -T frappe bash /mnt/scripts/production/backup.sh >> /var/log/payroll-backup.log 2>&1
#
# Exit non-zero on failure so the wrapping cron/alert can notify (see README §Alerts).
set -euo pipefail

SITE="${FRAPPE_SITE:-payroll.localhost}"
BENCH=~/frappe-bench
# Mount a host volume at this path in compose to persist backups OUTSIDE the container.
DEST="${BACKUP_DEST:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

cd "$BENCH"
mkdir -p "$DEST"

echo "[backup] $(date -u +%FT%TZ) starting backup of $SITE"
bench --site "$SITE" backup --with-files

SRC="$BENCH/sites/$SITE/private/backups"
# Copy the newest set (sql + files tars) to the durable destination.
STAMP="$(date -u +%Y%m%d_%H%M%S)"
mkdir -p "$DEST/$STAMP"
cp -v "$SRC"/*-database.sql.gz "$DEST/$STAMP/" 2>/dev/null || { echo "[backup] no DB dump produced"; exit 1; }
cp -v "$SRC"/*-files.tar         "$DEST/$STAMP/" 2>/dev/null || true
cp -v "$SRC"/*-private-files.tar "$DEST/$STAMP/" 2>/dev/null || true

# Integrity: the gzip dump must be readable.
gzip -t "$DEST/$STAMP/"*-database.sql.gz
echo "[backup] verified gzip integrity of the database dump"

# Retention: drop backup sets older than RETENTION_DAYS.
find "$DEST" -mindepth 1 -maxdepth 1 -type d -mtime +"$RETENTION_DAYS" -print -exec rm -rf {} + || true

echo "[backup] $(date -u +%FT%TZ) OK -> $DEST/$STAMP"
echo "[backup] REMINDER: replicate $DEST off-site (different host/region)."
