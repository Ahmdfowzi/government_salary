# Payroll locking & historical integrity smoke test (Phase 3 M3 / M3.1).
#
# The check now lives in the app as an importable function so it can run as a
# single process via `bench execute` — which fails hard on the first error
# (non-zero exit) and cannot print a false "PASSED":
#
#   docker compose -f docker/docker-compose.yml exec frappe \
#     bash -lc "cd ~/frappe-bench && bench --site payroll.localhost execute \
#       iraqi_government_payroll.smoke.checks.locking"
#
# This file remains a thin entry point: it is a single call, so even if fed to
# `bench console` the exception propagates and halts (no per-line false PASSED).
from iraqi_government_payroll.smoke.checks import locking

locking()
