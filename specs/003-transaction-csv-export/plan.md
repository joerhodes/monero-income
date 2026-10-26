# Implementation Plan: Transaction CSV Export

**Branch**: `003-transaction-csv-export` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-transaction-csv-export/spec.md`

## Summary

Every run that completes its sync and pricing ends by writing `xmr_income.csv` to the reports
directory: `--reports-path`, then the `reports_path` config key, then `~/reports`. The file
holds every recorded transaction with its UTC day's price.

- **Reading**: one read-only query joins transactions to their day's price.
- **Formatting**: pure functions sort the rows by (timestamp, height, txid) and format each
  column exactly. They use integer piconero, `Decimal` prices with format `"f"`, and a half-up
  rounding to the cent for `usd_value` only.
- **Writing**: a primitive writes a `0o600` temporary file in the same directory, `fsync`s it,
  and atomically renames it over the old export. It holds a lock on the directory so it can
  also remove temporary files a killed run left behind.
- **Failures**: a failed write fails the run (exit 1) and leaves the previous export intact.
  A successful run prints `Exported N transactions to <path>.`
- **Docs and golden files**: a standalone `docs/export-csv.md` documents the format for
  auditors. Golden files lock the bytes.

The feature follows feature 001/002's stack, layers, config, error handling and test
conventions; only the differences are listed here.

## Technical Context

**Language/Version, tooling, gates**: unchanged from feature 001 (Python 3.13+, uv, ruff,
mypy `--strict`, import-linter, pytest with a 90% coverage floor)

**New dependencies**: none (stdlib `csv`, `decimal`, `fcntl`, `os`, `tempfile`)

**Storage**: schema unchanged (version 2). The export only reads `transactions` and
`daily_prices`. The output is one file in the reports directory
([data-model.md](data-model.md))

**Testing**:
- Pure formatting and sorting: unit tests.
- `write_export`: tested against `tmp_path`, with row iterables that raise `OSError` or
  `KeyboardInterrupt` partway, a planted stale temporary file, a pre-existing `0o644` export,
  and an output path that's a file.
- `run()`: integration tests with the fake wallet and price source. The autouse `HOME`
  fixture keeps `~/reports` inside `tmp_path`.
- Golden files for a synthetic database and for an empty one.

**Target Platform**: Linux and macOS (unchanged). `fcntl.flock` on a directory descriptor is
POSIX-only, which matches.

**Project Type**: CLI application (single package, `src/` layout)

**Performance Goals**: none new. Writing is linear in transactions; a mining wallet with tens
of thousands of payouts writes in well under a second.

**Constraints**:
- No `float` (constitution III).
- No exponents or separators in the file (FR-018).
- Owner-only file and temporary file (FR-026).
- Never a partial file (FR-007).
- No export after any failure (FR-002).

**Scale/Scope**: the whole table is read into memory each run (one row object per
transaction); fine up to hundreds of thousands of rows.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.* Checked against
constitution v1.2.0.

| Principle | Status | How the design complies |
|-----------|--------|-------------------------|
| I. Layered architecture | ✅ | `primitives/export_db.py` (query) and `primitives/export_file.py` (atomic write); `orchestration/export_format.py` (pure) and `orchestration/export.py` (step); the CLI only gains `--reports-path` and one output line. The existing import-linter contracts cover the new modules. |
| II. Thin CLI | ✅ | The CLI passes `reports_path` in `CliOptions` and formats `RunResult.exported` into one line. Reading, formatting, writing and error translation live below it. |
| III. Exact money | ✅ | `xmr` comes from integer piconero by integer division. `usd_price` is `Decimal` from the stored text, written with format `"f"`. `usd_value` reuses feature 002's exact product, and only output rounding (`quantize`, half up) is applied, as the constitution allows ("exact … to the point they are output"). No `float` anywhere. |
| IV. Separate I/O from transformation | ✅ | The query returns records; `export_rows` sorts and formats them with no I/O; `write_export` writes given rows and doesn't format them. |
| V. Testable without the network | ✅ | No new external service. Files go to `tmp_path`; `HOME` is isolated; pytest-socket is still on. |
| VI. Data safety | ✅ | The export never writes to the database (FR-024). A failed export keeps every recorded row. No schema change, so no migration. |
| VII. Automated gates | ✅ | Unchanged. The 90% floor applies to the new modules. |
| Constraints: private data | ✅ | The export is `0o600` (FR-026). Golden files and test databases are synthetic. |
| Workflow / golden files | ✅ | The export is report output: its format is stated in the spec (FR-009–FR-018) and [contracts/export-csv.md](contracts/export-csv.md), and locked by new golden files in `tests/golden/` in this change. |

**Post-design re-check**: unchanged; no violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-transaction-csv-export/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── export-csv.md     # the file: location, encoding, columns, order, example
│   ├── cli.md            # --reports-path, the Exported line, the export write error
│   ├── config.md         # reports_path
│   └── run-api.md        # CliOptions.reports_path, ExportSummary, RunResult.exported
└── tasks.md              # /speckit-tasks
```

### Source Code (changes to feature 002's layout)

```text
src/monero_income/
├── cli.py                          # + --reports-path; + the Exported line
├── orchestration/
│   ├── __init__.py                 # + ExportSummary
│   ├── run.py                      # + export step after pricing; ExportWriteError → RunError
│   ├── settings.py                 # + reports_path key, option, default ~/reports
│   ├── export.py                   # NEW: read rows → export_rows → write_export; ExportSummary
│   └── export_format.py            # NEW, pure: HEADER, format_*, round_cents, export_rows
└── primitives/
    ├── errors.py                   # + ExportWriteError
    ├── models.py                   # + ExportRecord
    ├── export_db.py                # NEW: export_records(conn)
    └── export_file.py              # NEW: write_export (lock, clean, temp 0o600, fsync, replace)

tests/
├── golden/
│   ├── xmr_income.csv              # NEW: synthetic database's export (research R8)
│   └── xmr_income_empty.csv        # NEW: header only
├── unit/test_export_format.py      # columns, rounding, order, no exponents/separators
├── adapters/test_export_file.py    # atomic replace, 0o600, interrupt/failure, stale temp, lock
├── adapters/test_export_db.py      # join, NULL prices, decimal text round-trip
├── integration/test_export.py      # run() writes/doesn't write; golden comparison; paths
└── cli/                            # --reports-path mapping; Exported line; write error

docs/export-csv.md                  # NEW: reader documentation (FR-023)
README.md                           # Usage: reports_path, --reports-path, link to docs
```

**Structure Decision**: same single package and layers as features 001 and 002. The export
gets its own orchestration and primitives modules, so sync and pricing stay unchanged.

## Complexity Tracking

No violations.
