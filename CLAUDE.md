# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

All 5 phases of `development_plan.md` are **complete** — the MVP (PRD §12.1) is implemented end to end. 54 tests passing.

Architecture: `src/models/` (Pydantic domain models, rules-as-data), `src/dataio/` (Excel reader behind a `DataReader` interface), `src/engine/` (`validators.py` = pure vectorized mask functions 1:1 with `ErrorType`; `validation_engine.py` = orchestration + `ErrorRecord` assembly; `result.py` = `ValidationResult` aggregation), `src/reporting/` (per-owner Excel report writer, grouped by responsible email), `src/mailer/` (`config` from `.env`, `templates`, `smtp_client` with a `dry_run` mode), `src/storage/` (SQLAlchemy/SQLite: `orm.py` tables, `db.py` connection, `repositories.py` for template/mapping CRUD + validation/mail history), `src/ui/` (Streamlit step pages: upload → mapping → rules → results → mail, navigated via `state.py` session state).

Key conventions: email sending has a **`dry_run`** path so the full flow is testable without a real SMTP server; SMTP creds come from `.env` (see `.env.example`). Reports → `REPORT_DIR` (default `data/reports`); DB → `DB_PATH` (default `data/validation.db`). Phase-2 deferrals still open: conditional validation (§5.3.8, model interface only), PDF reports, dashboards, approval workflow (PRD §12.2).

Run the app: `streamlit run app.py` (root `app.py` re-exports `src.app:main` so the package's relative imports resolve). Generate test data: `python scripts/generate_sample.py` → `data/sample_maintenance.xlsx`.

Key documents:
- `data_validation_prd.md` — the full product requirements (in Korean). **This is the source of truth.**
- `development_plan.md` — the phased build plan with per-phase scope and completion criteria.

## Environment & commands

```bash
source venv627/bin/activate          # Python 3.13 venv
pip install -r requirements.txt      # install deps
python -m pytest                     # run all tests
python -m pytest tests/test_models.py::test_rule_template_json_roundtrip  # single test
```

The directory name contains a space (`Data Validation System`), so always quote paths in shell commands.

Note: the I/O package is named `src/dataio/` (not `io/` as the plan sketches) to avoid shadowing Python's stdlib `io`.

## What this product is

**Maintenance Data Validation & Error Report System** — a tool for validating maintenance data for offshore-plant equipment/parts that arrives as Excel files from many contributors, then generating per-owner error reports and emailing them.

End-to-end flow (PRD §7): upload Excel → select sheet → auto-detect columns → map columns → choose/define a validation Rule Template → run validation → review errors → generate per-owner reports → preview & send email → persist validation and send history.

## Core domain concepts

These drive the whole design; keep them decoupled so they can evolve independently:

- **Column mapping** (PRD §5.2, §14.1) — uploaded Excel column names are *not* fixed. Everything works through a mapping from uploaded columns to system canonical columns (e.g. `Data ID`, `Responsible Person`, `Responsible Email`). Never hard-code source column names. The three columns required for per-owner reporting are `Data ID`, `Responsible Person`, `Responsible Email`; missing ones become their own error class (`Column Mapping Error`).

- **Validation rules** (PRD §5.3) — per-column rules: required, data type (Text/Number/Integer/Decimal/Date/Email/Boolean/Code-List/URL), numeric min/max, allowed-list, date constraints (format, future/past allowed, before/after a reference date), email format, duplicate (single column or column combination), and conditional rules (one column's requirement/allowed-values depend on another column's value).

- **Rule Templates** (PRD §5.4) — named, reusable sets of column rules. Treat rules as data, not code, so templates can be created/edited/copied/deleted and re-applied for re-validation.

- **Error types** (PRD §9) — the canonical set: `Missing Required Value`, `Invalid Data Type`, `Out of Range`, `Invalid List Value`, `Invalid Date Format`, `Invalid Email Format`, `Duplicate Value`, `Conditional Rule Error`, `Column Mapping Error`. Use these exact identifiers as the error taxonomy.

- **Error records** (PRD §5.5, §8.3) — each error carries: Data ID, Row Number, Column Name, Input Value, Error Type, Error Message, Responsible Person, Responsible Email. Reports group these by responsible person/email.

## Design constraints to respect

- **Never mutate the uploaded file** (PRD §14.4). Validation reads the original; reports are always separate generated files.
- **Error messages are data** (PRD §14.3) — provide a default message per error type, but allow per-column overrides. Don't bury message text in validation logic.
- **No-code rule setup** (PRD §10.3) — rules and templates are configured by end users, never by editing code.
- **Re-validation** (PRD §14.5) — a resubmitted file must be re-runnable against the same Rule Template, so template application must be deterministic and repeatable.
- **Performance target** (PRD §10.1) — ≤10,000 rows should validate within ~1 minute; ≥100,000 rows should use batch/async processing. Prefer vectorized validation over per-cell Python loops.

## MVP scope (build this first — PRD §12.1)

Excel upload, sheet selection, column auto-detection, per-column rule setup, and these validators: required, data type, numeric range, allowed-list, email format, duplicate. Then: results screen, per-owner Excel report generation, per-owner email send, and validation-history persistence.

Deferred to phase 2 (PRD §12.2): advanced conditional validation, PDF reports, dashboards, project-scoped templates, re-validation comparison, internal mail-system/API integration, approval workflow.

## Suggested implementation notes

- Excel I/O: `openpyxl`/`pandas` are the natural fit for `.xlsx`/`.xls` reading and report generation. CSV support is a planned extension (PRD §10.4), so keep the reader behind an interface.
- Validators map one-to-one onto the error types above — implement each as an independent, testable rule that takes a column's values + rule config and yields error records. This keeps the engine extensible (PRD §10.4) and aligns naturally with unit tests per rule.
- Roles (Admin / Validator / Reviewer / Data Owner, PRD §11) gate features; design with an authorization seam even if MVP runs single-user.

## When you add tooling

Once dependencies, tests, or a runner exist, replace the "Project status" section above with the real build/test/run commands (including how to run a single test) so future sessions don't have to rediscover them.
