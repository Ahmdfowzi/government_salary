#!/usr/bin/env bash
# Run INSIDE the frappe container (from the project root on the host):
#   docker compose -f docker/docker-compose.yml exec frappe bash /mnt/scripts/install-app.sh
#
# Initializes a bench, creates a site, installs THIS app from the bind-mounted
# path via an EDITABLE install (not `bench get-app`, which treats a local path
# like a git remote and fails), migrates, and prints fixture counts. Idempotent:
# skips bench init, site creation, app linking and apps.txt registration if
# already present.
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

APP_NAME="iraqi_government_payroll"
echo ">> install local app from bind mount (editable; not 'bench get-app')"
# bench get-app treats a local path like a git remote, so instead link the
# bind-mounted app into apps/ and install it editable.
if [ ! -e "apps/$APP_NAME" ]; then
  if [ -f "$APP_SRC/pyproject.toml" ] || [ -f "$APP_SRC/setup.py" ]; then
    ln -s "$APP_SRC" "apps/$APP_NAME"        # bind mount is read-write; live edits reflected
  else
    cp -a "$APP_SRC" "apps/$APP_NAME"        # fallback if layout differs
  fi
fi
# register the app with the bench (idempotent)
touch sites/apps.txt
grep -qxF "$APP_NAME" sites/apps.txt || echo "$APP_NAME" >> sites/apps.txt
# editable install into the bench python env (equivalent of get-app's pip step)
bench pip install -e "apps/$APP_NAME" || ./env/bin/python -m pip install -e "apps/$APP_NAME"
# ensure app python requirements are present (required step; non-fatal)
bench setup requirements --python || true

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
