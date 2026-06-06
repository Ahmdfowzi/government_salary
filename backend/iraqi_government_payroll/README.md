# iraqi_government_payroll

Frappe/ERPNext custom app — production payroll system for Iraqi government
employees (module: **Government Payroll**).

This is the installable Frappe app root (the package and `hooks.py` live under
`iraqi_government_payroll/`). It provides the versioned rule-set data model,
the payroll calculation engines (active salary, income tax, pension, increment,
promotion), salary slips and batch payroll runs.

- Architecture & engine boundaries: see `../../ENGINE-BOUNDARIES.md`
- Bench / Docker installation: see `../../BENCH-READINESS.md` and `../../docker/`

## Install (editable, inside a bench)
```bash
bench pip install -e apps/iraqi_government_payroll
bench --site <site> install-app iraqi_government_payroll
bench --site <site> migrate
```

## License
MIT
