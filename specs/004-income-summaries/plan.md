# Implementation Plan: On-Screen Income Summaries

**Branch**: `004-income-summaries` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-income-summaries/spec.md`

## Summary

Every successful run ends, after the export line, with three income summaries: the last 26
ISO weeks, 12 months, and 4 years, each ending with the current period, in the summary time
zone. That zone is `--timezone`, then the `timezone` config key, then the machine's local
time zone.

- **Data**: the summary step reads the same records as the export, with a second read in the
  same snapshot, so the two always agree (research R1). No schema change and no new query.
- **Aggregation**: pure functions group records by their local date. XMR is summed as `int`
  piconero and USD as exact `Decimal` values of feature 002's `usd_value`. The flags record
  provisional and unpriced transactions.
- **Rendering**: rich, as in the original tool (research R7).
  - Each summary is a `Table(box=box.ROUNDED, header_style="bold")`.
  - The side-by-side layout is a rich grid, chosen from the terminal width the CLI passes
    (`None` when the output isn't a terminal).
  - Everything is rendered into an in-memory `Console` with an explicit width, and the CLI
    echoes the text.
  - Formatting covers grouped XMR, `$`-grouped USD rounded once half up, and the `*`/`?`
    marks and their legend.
- **Time zone**: validated in two steps. `resolve_settings` checks the type and that the value
  isn't empty. A new primitive then loads the name against the system's time zone database,
  before syncing. With no setting, conversion uses the system's local rules through
  `astimezone(None)`.
- **Safeguard (FR-018)**: the whole summary step is guarded: reading, computing, and
  rendering. Any failure there becomes one clean `SummaryError`. The run prints features
  001–003's lines, then the error, and exits 1, with the export as written. The lines are
  built completely before anything is printed, so no partial summary appears (research R10).
- **Golden files**: they lock both layouts, the unmarked case, and the no-transactions
  message.

The feature follows features 001–003's stack, layers, config, error handling and test
conventions; only the differences are listed here.

## Technical Context

**Language/Version, tooling, gates**: unchanged from feature 001 (Python 3.13+, uv, ruff,
mypy `--strict`, import-linter, pytest with a 90% coverage floor)

**New dependencies**: `rich>=15.0.0`, declared directly in `pyproject.toml`. It was already
installed as Typer's dependency at 15.0.0, so `uv.lock` only records the direct dependency.
The rest is stdlib (`zoneinfo`, `datetime`, `decimal`, `shutil`, `io`). The time zone database
is the system's (`/usr/share/zoneinfo` on macOS and Linux; research R2).

**Storage**: schema unchanged (version 2). The summaries reuse the records from feature 003's
`export_records`, and nothing is written ([data-model.md](data-model.md)).

**Testing**:
- **Aggregation**: unit tests with synthetic `ExportRecord`s and explicit `ZoneInfo`s. They
  cover ranges, ISO week years (2026-W53), local-midnight cases on both sides of a DST change,
  exact sums, flags, and records outside the range.
- **System zone**: a fixture sets `TZ` and calls `time.tzset()`, restoring both afterwards.
- **Rendering**:
  - unit tests and golden files for both layouts, the unmarked case, and the message;
  - every rendering goes into a rich `Console` with an explicit width and no color system,
    so the output is deterministic;
  - golden comparisons strip trailing spaces per line (research R9);
  - the width threshold is tested at *W* − 1 and *W*, and a width narrower than one table
    still shows every figure in full.
- **Settings and loading**: unit tests for `timezone` and `load_zone`.
- **`run()`**: integration tests with the fake wallet, price source and clock. They check
  that `summaries` is set and agrees with the export, that an invalid time zone fails before
  syncing, and that a failed run returns no summaries.
- **CLI**: the blank line, the placement after the export line, the `isatty`/width/styled
  plumbing (with a fake `RunResult`), no ANSI codes when not a terminal, and `--timezone`
  mapping onto `CliOptions`.
- **Summary-step failures (FR-018)**: one injected failure per stage (research R10):
  - **reading**: a `summary_reader` raising `StorageReadError("invalid stored price 'abc'")`
    or `RuntimeError`;
  - **computing**: records with a `NaN` price, a negative amount, or a status without a
    price;
  - **rendering**: a malformed `IncomeSummaries`, or a renderer patched to raise.

  Each test asserts that stdout holds exactly the earlier lines, including `Exported …`, and
  no summary line. It also checks the single `Error: cannot show the income summaries: …`
  line on stderr, exit status 1, and an export byte-identical to the one the run wrote.

**Target Platform**: Linux and macOS (unchanged). `time.tzset()` in tests is POSIX-only,
which matches.

**Project Type**: CLI application (single package, `src/` layout)

**Performance Goals**: SC-007, under one second for 100,000 transactions. Measured during
planning: the exact sum takes 5 ms and the date conversion 63 ms per 100,000 records. A
`test_performance.py` case covers it.

**Constraints**:
- No `float` (constitution III).
- Figures, labels and marks are ASCII; the borders are rich's `box.ROUNDED`.
- Plain text, with no ANSI codes, when the output isn't a terminal.
- Lines no wider than the terminal in the side-by-side layout (US3-4).
- rich is never given a console narrower than the layout, so no figure is truncated.
- At most 40 lines side by side (SC-006); 36 in the contract example (research R7).

**Scale/Scope**: one pass over the records per summary; memory is the record list that
feature 003 already holds.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.* Checked against
constitution v1.2.0.

| Principle | Status | How the design complies |
|-----------|--------|-------------------------|
| I. Layered architecture | ✅ | `primitives/timezones.py` (loading a zone). `orchestration/summary.py` (pure aggregation) and `orchestration/summary_format.py` (pure rendering with rich into an in-memory console). The CLI gains `--timezone` and prints the rendered text. The existing import-linter contracts cover the new modules; rich is third-party, outside the layers. |
| II. Thin CLI | ✅ | The CLI passes `timezone` in `CliOptions`. It measures the terminal (`isatty`, `get_terminal_size`), which is presentation, and echoes the text from `summary_text(...)`. Aggregation, the rich tables, layout and text all live in orchestration and can be tested without Typer. |
| III. Exact money | ✅ | XMR is an `int` sum of piconero, formatted by integer `divmod`. USD is the exact `Decimal` sum of feature 002's exact products, in a context that traps `Inexact`. It is rounded once, at output, with feature 003's `round_cents`. No `float` anywhere. |
| IV. Separate I/O from transformation | ✅ | `load_zone` reads the time zone database and does nothing else. `build_summaries` and `render_text` take values and return values; `render_text` writes only to an in-memory rich `Console`. Reading the records is feature 003's existing primitive. |
| V. Testable without the network | ✅ | No new external service. The system zone is controlled by `TZ` in tests; pytest-socket is still on. |
| VI. Data safety | ✅ | Nothing is written to the database or the export (FR-017). No schema change, so no migration. |
| VII. Automated gates | ✅ | Unchanged. The 90% floor applies to the new modules. |
| Constraints: private data | ✅ | Golden files and test records are synthetic. The summaries are only printed, never written to a file. |
| Workflow / golden files | ✅ | The summaries are report output. Their format is stated in the spec (FR-007–FR-016) and in [contracts/summaries.md](contracts/summaries.md), and locked by new golden files in `tests/golden/` in this change. Feature 003's export golden files are unchanged. |

**Post-design re-check**: unchanged; no violations.
- **FR-018**: kept as a deliberate safeguard. The summary step's three stages are guarded,
  and every failure there maps to a clean run error with no traceback (feature 001's rule;
  research R10).
- **Broad catch**: catching `Exception` is confined to that step, and `KeyboardInterrupt`
  still propagates.

## Project Structure

### Documentation (this feature)

```text
specs/004-income-summaries/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── summaries.md      # the text: ranges, tables, marks, legend, layouts, example
│   ├── cli.md            # --timezone, output placement, the time zone error
│   ├── config.md         # timezone
│   └── run-api.md        # CliOptions.timezone, IncomeSummaries, RunResult.summaries, render_text, summary_text
└── tasks.md              # /speckit-tasks
```

### Source Code (changes to feature 003's layout)

```text
src/monero_income/
├── cli.py                          # + --timezone; + blank line and the summary text
├── orchestration/
│   ├── __init__.py                 # + IncomeSummaries, Summary, PeriodFigures, render_text, summary_text
│   ├── run.py                      # + load zone; summary read in the export's snapshot; build; SummaryError
│   ├── settings.py                 # + timezone key and option (type and empty checks)
│   ├── summary.py                  # NEW, pure: record checks, periods, labels, exact sums, flags, build
│   └── summary_format.py           # NEW, pure: input checks, formats, marks; rich tables and layouts; render_text, summary_text
└── primitives/
    ├── errors.py                   # + UnknownTimeZoneError
    └── timezones.py                # NEW: load_zone(name)

tests/
├── golden/
│   ├── summaries_side_by_side.txt  # NEW (research R9)
│   ├── summaries_sequential.txt    # NEW
│   ├── summaries_unmarked.txt      # NEW
│   └── summaries_empty.txt         # NEW
├── conftest.py                     # + local_tz fixture (TZ + tzset, restored)
├── unit/test_summary.py            # ranges, ISO years, local dates, sums, flags, out-of-range
├── unit/test_summary_format.py     # formats, marks, rich table style, widths, threshold, no truncation
├── unit/test_settings.py           # + timezone
├── adapters/test_timezones.py      # load_zone: known, unknown, wrong case, path-like names
├── integration/test_summaries.py   # run() sets summaries; agrees with export; golden
├── integration/test_summary_failures.py # NEW: reading/computing failures → SummaryError; export kept
├── integration/test_performance.py # + 100,000 records under one second
└── cli/                            # --timezone mapping; placement; width plumbing; FR-018 output and exit

pyproject.toml                      # + rich>=15.0.0 (direct dependency; uv.lock updated)
README.md                           # Usage: timezone, --timezone, the summaries; Status table
```

**Structure Decision**: the same single package and layers as features 001–003. The
summaries get their own orchestration modules, and the export step is unchanged.

## Complexity Tracking

No violations.
