# Data Model: On-Screen Income Summaries

**Feature**: 004-income-summaries | **Date**: 2026-10-27

## Persistent schema

**Unchanged** (version 2). The summaries read the same records as feature 003's
`export_records(conn)`, with a second read in the same snapshot (research R1), and write
nothing (FR-017). No migration.

## Settings

| Type | New field | Type | Default |
|------|-----------|------|---------|
| `CliOptions` | `timezone` | `str \| None` | `None` (not given) |
| `Settings` | `timezone` | `str \| None` | `None` = the machine's local time zone |

`resolve_settings` validates the type and that the value isn't empty
([contracts/config.md](contracts/config.md)), and adds `"timezone"` to `STRING_KEYS`. `run()`
turns the name into a `ZoneInfo` with `load_zone` before opening the database.

## In-memory types

All are frozen dataclasses. XMR is `int` piconero and USD `Decimal`; never `float`.

### `PeriodFigures` (orchestration/summary.py): one row, or a total

| Field | Type | Rule |
|-------|------|------|
| `label` | `str` | `YYYY-Www`, `YYYY-MM`, `YYYY`, or `Total` |
| `piconero` | `int` | Sum of every transaction's amount in the period (FR-009) |
| `usd` | `Decimal` | Exact sum of `usd_value(amount, price)` over its priced transactions; `Decimal(0)` if none (FR-010) |
| `provisional` | `bool` | Any transaction valued at a `provisional` price (FR-012) |
| `unpriced` | `bool` | Any transaction with no price (FR-012) |

For a total, `piconero` and `usd` are the exact sums over the summary's periods, and the flags
are the `any` of the periods' flags (FR-011).

### `Summary` (orchestration/summary.py)

| Field | Type | Meaning |
|-------|------|---------|
| `title` | `str` | `Weekly Summary`, `Monthly Summary`, or `Annual Summary` |
| `periods` | `tuple[PeriodFigures, ...]` | 26, 12, or 4 periods, oldest first, ending with the current one (FR-002, FR-007) |
| `total` | `PeriodFigures` | Label `Total` |

### `IncomeSummaries` (orchestration/summary.py)

| Field | Type | Meaning |
|-------|------|---------|
| `weekly`, `monthly`, `annual` | `Summary` | The three summaries |
| `transactions` | `int` | Count of all recorded transactions. With 0, the message replaces the summaries (FR-016) |

### `RunResult` (orchestration/run.py): gains one field

| Field | Type | Meaning |
|-------|------|---------|
| `summaries` | `IncomeSummaries \| None` | Set by every successful `run()`. `None` only as the default, so existing test constructions keep working |

## Pure transformations

There is no I/O in either module (constitution IV). The only environment they depend on is
the process's local time zone rules, when `zone` is `None` (research R2).

### orchestration/summary.py: aggregation

| Function | Input → output | Rule |
|----------|----------------|------|
| `local_date` | `(int, ZoneInfo \| None)` → `date` | `datetime.fromtimestamp(ts, UTC).astimezone(zone).date()` |
| `week_label` | `date` → `str` | `f"{y}-W{w:02d}"` from `isocalendar()` |
| `month_label`, `year_label` | `date` → `str` | `YYYY-MM`, `YYYY` |
| `week_labels(today)` | → 26 labels | The Mondays of the 26 ISO weeks ending with today's, oldest first |
| `month_labels(today)`, `year_labels(today)` | → 12 or 4 labels | Calendar months or years ending with today's, oldest first |
| `exact_sum` | `Iterable[Decimal]` → `Decimal` | Added with `prec = MAX_PREC` and `Inexact` trapped (research R4) |
| `summarize` | `(records, labels, label_of, title)` → `Summary` | One pass. Records whose label isn't in `labels` are skipped |
| `check_record` | `ExportRecord` → `None` | Raises `SummaryDataError` naming the txid unless the record meets the invariants in research R10 |
| `build_summaries` | `(Sequence[ExportRecord], today: date, zone)` → `IncomeSummaries` | Checks every record, then builds the three summaries plus the record count |
| `summary_failure_message` | `(reason: str, export_path: Path)` → `str` | The contracts/cli.md FR-018 message. Here rather than in `summary_format.py`, which imports `run.py`, so that `run.py` and `summary_format.py` can both use it without importing each other |

`usd_value` (feature 002, `orchestration/valuation.py`) is reused unchanged.

### orchestration/summary_format.py: text, with rich

Builds rich renderables and renders them into an in-memory `Console` (research R7). There is
no terminal and no file I/O.

| Function | Input → output | Rule |
|----------|----------------|------|
| `format_xmr_grouped` | `int` → `str` | `f"{whole:,}.{fraction:012d}"` (research R5) |
| `format_usd` | `Decimal` → `str` | `"$" + format(round_cents(value), ",f")`; `round_cents` from feature 003's `export_format` |
| `marks` | `PeriodFigures` → `str` | `""`, `"*"`, `"?"`, or `"*?"` |
| `check_summaries` | `IncomeSummaries` → `None` | 26/12/4 periods, non-negative `int` XMR, finite non-negative `Decimal` USD; `SummaryDataError` otherwise |
| `summary_table` | `Summary` → `rich.table.Table` | `Table(title=..., box=box.ROUNDED, header_style="bold")`; columns Period (left), XMR and USD (right), `no_wrap`; `Text` cells; `add_section()` before `Total`; marks padded into the USD cell ([contracts/summaries.md](contracts/summaries.md)) |
| `table_width` | `Table` → `int` | `Measurement.get(...).maximum` on a probe `Console(width=10_000)` |
| `side_by_side_width` | `IncomeSummaries` → `int` | weekly + 4 + max(monthly, annual) |
| `summary_renderable` | `(IncomeSummaries, int \| None)` → `(RenderableType, int)` | The chosen layout (grid or stacked `Group`) plus legend, or `NO_TRANSACTIONS`, and the width it needs: the layout's width or the longest legend line shown, whichever is larger |
| `render_text` | `(IncomeSummaries, int \| None, bool)` → `str` | `check_summaries`, then print `summary_renderable` into `Console(file=StringIO(), width=max(width or 0, needed), color_system="standard" if styled else None, force_terminal=styled, highlight=False, markup=False, emoji=False, legacy_windows=False)` and return the text |
| `summary_text` | `(RunResult, Path, int \| None, bool)` → `str` | The guarded rendering stage: the complete text, or `SummaryError` (research R10). The `Path` is the export the run wrote, passed in by the CLI, and is named in the error message |
| `LEGEND`, `NO_TRANSACTIONS` | constants | Texts from the contract |

## Primitives

| Module | Function | Kind | Behavior |
|--------|----------|------|----------|
| `primitives/timezones.py` | `load_zone(name) -> ZoneInfo` | I/O (reads the system's time zone files) | Returns `ZoneInfo(name)` if `name in zoneinfo.available_timezones()`. Otherwise, or on `ZoneInfoNotFoundError`/`ValueError`/`OSError`, raises `UnknownTimeZoneError` |

New error in `primitives/errors.py`: `UnknownTimeZoneError(Exception)`, whose message is the
name. `run()` turns it into `RunError(f"invalid timezone: unknown time zone '{name}'")`.

## Errors for the summary step (FR-018, research R10)

| Error | Module | Meaning |
|-------|--------|---------|
| `SummaryDataError(Exception)` | `orchestration/summary.py` | A record or an `IncomeSummaries` breaks an invariant; the message names the transaction id or the field, never amounts or secrets |
| `SummaryError(RunError)` | `orchestration/run.py` (beside `RunResult`, which it carries) | The summary step failed after the export was written. Carries `result: RunResult` (steps 1–4, `summaries=None`); its message is the contracts/cli.md line |

## Changes to feature 003's export step

None. `read_export_rows(conn)` and `write_export_file(directory, rows)` are unchanged, and
the export's bytes are unchanged; the feature 003 golden files must still pass. The summary
step's read is separate (`summary_reader`, defaulting to `export_records`) and runs right
after `read_export_rows`, before the database is closed.

## State: what a run prints after the export line

| Run outcome | After the `Exported …` line |
|-------------|-----------------------------|
| Invalid settings (including `timezone`), sync failure, storage error in the export's read, invalid import file, export write failure | Nothing: no export line and no summaries |
| Success, no transactions recorded | Blank line, `No transactions to summarize yet.` |
| Success, transactions recorded, no marks | Blank line, the three summaries |
| Success, with provisional or unpriced figures | Blank line, the three summaries, blank line, the legend |
| Summary step fails (reading, unexpected data, computing, rendering) | Nothing on stdout; `Error: cannot show the income summaries: …` on stderr; exit 1; the export as written |
