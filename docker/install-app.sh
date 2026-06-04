#!/usr/bin/env bash
# Run INSIDE the frappe container:
#   docker compose -f docker/docker-compose.yml exec frappe bash
#   bash /mnt/iraqi_government_payroll/../.. ? -> simplest: copy/paste the steps below,
#   or: docker compose -f docker/docker-compose.yml exec frappe bash /mnt/install-helper
#
# This script initializes a bench, creates a site, installs THIS app from the
# bind-mounted path, migrates, and prints fixture counts. Idempotent-ish: it
# skips bench init / site creation if they already exist.
set -euo pipefail

BENCH_DIR="$HOME/frappe-bench"
SITE="payroll.localhost"
APP_SRC="/mnt/iraqi_government_payroll"
FRAPPE_BRANCH="version-15"

if [ ! -d "$BENCH_DIR" ]; then
  echo ">> bench init ($FRAPPE_BRANCH)"
  bench init --skip-redis-config-generation --frappe-branch "$FRAPPE_BRANCH" "$BENCH_DIR"
fi
cd "$BENCH_DIR"

echo ">> point bench at the compose services"
bench set-config -g db_host mariadb
bench set-config -g redis_cache    redis://redis-cache:6379
bench set-config -g redis_queue    redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379

if [ ! -d "sites/$SITE" ]; then
  echo ">> new-site $SITE"
  bench new-site "$SITE" --no-mariadb-socket --db-root-password 123 --admin-password admin
fi
bench --site "$SITE" set-config developer_mode 1

echo ">> get-app from bind mount"
if [ ! -d "apps/iraqi_government_payroll" ]; then
  bench get-app "$APP_SRC"
fi

echo ">> install-app + migrate"
bench --site "$SITE" install-app iraqi_government_payroll || true
bench --site "$SITE" migrate

echo ">> fixture counts (expect: scale 143 | qual 16 | brackets 4 | durations 9 | roles 6 | doctypes 27)"
bench --site "$SITE" console <<'PY'
import frappe
print("Rule Sets          :", frappe.db.count("Government Rule Set"))
print("Scale detail (143) :", frappe.db.count("Government Salary Scale Detail"))
print("Qual rules (16)    :", frappe.db.count("Qualification Appointment Rule"))
print("Tax brackets (4)   :", frappe.db.count("Income Tax Bracket"))
print("Promo durations(9) :", frappe.db.count("Promotion Grade Duration"))
print("Roles (6)          :", frappe.db.count("Role", {"role_name":["in",["Payroll Administrator","Payroll Manager","Payroll Officer","HR User","Finance User","Auditor"]]}))
print("Custom DocTypes(27):", frappe.db.count("DocType", {"module":"Government Payroll"}))
PY
echo ">> done. Site: http://localhost:8000  (start with: bench start)"
