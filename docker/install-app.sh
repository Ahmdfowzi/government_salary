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

# Pin the bench Python to a Frappe v15-supported version. The frappe/bench image
# ships Python 3.14 as the pyenv default, but Frappe v15 supports 3.10-3.12 only;
# under 3.14 the document-save path hits a Frappe-core file_lock TOCTOU
# (check_if_locked -> lock_age().stat() FileNotFoundError). 3.12.12 ships in the
# image. We force the bench virtualenv onto it.
PY_VERSION="3.12.12"
PY_BIN="$HOME/.pyenv/versions/$PY_VERSION/bin/python3"
if [ ! -x "$PY_BIN" ]; then
  PY_BIN="$(command -v python3.12 || command -v python3)"
fi
echo ">> pinned bench Python: $PY_BIN ($("$PY_BIN" --version 2>&1))"

if [ ! -d "$BENCH_DIR" ]; then
  echo ">> bench init ($FRAPPE_BRANCH, Python $PY_VERSION)"
  bench init --skip-redis-config-generation --python "$PY_BIN" \
    --frappe-branch "$FRAPPE_BRANCH" "$BENCH_DIR"
fi
cd "$BENCH_DIR"

# Self-heal: if an already-initialized bench env is on the wrong Python (e.g. a
# 3.14 bench built before this pin), rebuild only the virtualenv onto the pinned
# version. The site and database are untouched, so no re-migrate / re-seed is
# needed — just a Python swap.
CUR_PY="$(./env/bin/python -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo none)"
PIN_MM="${PY_VERSION%.*}"
if [ "$CUR_PY" != "$PIN_MM" ]; then
  echo ">> rebuilding bench env with Python $PY_VERSION (was: $CUR_PY)"
  rm -rf env
  "$PY_BIN" -m venv env
  ./env/bin/python -m pip install --quiet --upgrade pip wheel
  ./env/bin/python -m pip install --quiet -e apps/frappe
  for extra in apps/*/; do
    name="$(basename "$extra")"
    [ "$name" = "frappe" ] && continue
    [ -f "$extra/pyproject.toml" ] || [ -f "$extra/setup.py" ] && \
      ./env/bin/python -m pip install --quiet -e "$extra" || true
  done
  bench setup requirements || true
fi

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
# register the app in sites/apps.txt — newline-safe and self-repairing.
# A bare `echo >>` onto a file whose last line has no trailing newline produces
# "frappe<app>" on one line, which Frappe then tries to import as a single module
# (ModuleNotFoundError: No module named 'frappeiraqi_government_payroll').
touch sites/apps.txt
python3 - "$APP_NAME" <<'PY'
import os, sys
app = sys.argv[1]
path = "sites/apps.txt"
tokens = open(path).read().split() if os.path.exists(path) else []   # tolerant of missing newlines
repaired = []
for t in tokens:
    # split a concatenated "frappe<app>" token back into two apps
    if t != "frappe" and t.startswith("frappe") and t.endswith(app):
        repaired += ["frappe", app]
    else:
        repaired.append(t)
if "frappe" not in repaired:
    repaired.insert(0, "frappe")
if app not in repaired:
    repaired.append(app)
seen, out = set(), []
for t in repaired:
    if t not in seen:
        seen.add(t); out.append(t)
open(path, "w").write("\n".join(out) + "\n")
print("apps.txt ->", out)
PY
# editable install into the bench python env (equivalent of get-app's pip step)
bench pip install -e "apps/$APP_NAME" || ./env/bin/python -m pip install -e "apps/$APP_NAME"
# ensure app python requirements are present (required step; non-fatal)
bench setup requirements --python || true

echo ">> install-app + migrate"
bench --site "$SITE" install-app iraqi_government_payroll || true
bench --site "$SITE" migrate

echo ">> fixture counts (expect: scale 143 | qual 16 | brackets 4 | durations 9 | roles 6 | doctypes 34)"
bench --site "$SITE" console <<'PY'
import frappe
print("Rule Sets          :", frappe.db.count("Government Rule Set"))
print("Scale detail (143) :", frappe.db.count("Government Salary Scale Detail"))
print("Qual rules (16)    :", frappe.db.count("Qualification Appointment Rule"))
print("Tax brackets (4)   :", frappe.db.count("Income Tax Bracket"))
print("Promo durations(9) :", frappe.db.count("Promotion Grade Duration"))
print("Roles (6)          :", frappe.db.count("Role", {"role_name":["in",["Payroll Administrator","Payroll Manager","Payroll Officer","HR User","Finance User","Auditor"]]}))
print("Custom DocTypes(34):", frappe.db.count("DocType", {"module":"Government Payroll"}))
PY
echo ">> done. Site: http://localhost:8000  (start with: bench start)"
