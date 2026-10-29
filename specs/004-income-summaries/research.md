# Research: On-Screen Income Summaries

**Feature**: 004-income-summaries | **Date**: 2026-10-27

The spec left no `[NEEDS CLARIFICATION]` markers. These are the design decisions planning had
to make. Each lists the decision, why, and what else was considered.

## R1. The summary step reads its own records, in the export's snapshot

**Decision**:
- **Reads**: the summary step has its own read, `summary_reader(conn)`, which defaults to
  feature 003's `export_records`. `run()` makes it right after the export's read, on the same
  connection, before closing the database.
- **Same snapshot**: connections are opened with `autocommit=False`, so both reads run in the
  same implicit read transaction, with no commit between them, and see the same snapshot.
  The export and the summaries therefore show the same data (FR-019).
- **Deferred failure**: a failure of the summary read is caught and kept. The export is still
  written, and the failure is then reported through the summary-step guard (R10).
- **Build after the export**: the summaries are built from the summary records after the
  export is written.

**Rationale**:
- FR-018 is a deliberate safeguard. Giving the summary step its own read makes "reading" one
  of its guarded stages, and that stage can be tested by injecting a reader.
- Sharing one snapshot keeps FR-019 without sharing a single failure point with the export.
  A read failure in the export's own read still fails the run before the export, as in
  feature 003 (FR-002).
- Reading twice costs one more query.

**Note on stored prices**: a stored price that doesn't parse is rejected by the export's read
first, so in a real database it fails the run under feature 003's rules (no export written).
Tests of FR-018's "unexpected data" stage therefore inject a summary reader that raises the
same `StorageReadError` (`invalid stored price …`) or returns records that break the
summaries' invariants (R10).

**Alternatives considered**:
- **Sharing the export's records**: simplest, but the summary step would then have no
  reading stage of its own. A read failure could only happen before the export, so FR-018's
  read case would be untestable.
- **A second read after the export, on a new connection**: another run could commit in
  between, so the export and the summaries could disagree.
- **Aggregating in SQL** (`GROUP BY` week): SQLite has no ISO week or time zone support, and
  the sums would have to be exact over decimal text. Doing it in Python is simpler and exact.

## R2. Time zones: configured name, or the system's local rules

**Decision**:
- **Setting**: a new string config key `timezone` and a new option `--timezone`. Precedence is
  option, then file, then the machine's local time zone (clarification Q2).
- **Validation**:
  - `resolve_settings` (pure) checks the type and that the value isn't empty or blank, with
    the same message shapes as `reports_path`.
  - `run()` then loads the zone through a new primitive, `load_zone(name)`, before opening the
    database. An unknown name is a `RunError` before syncing (FR-006).
- **Known names**: a name is known when it is in `zoneinfo.available_timezones()` (the
  system's IANA time zone database). The check is case-sensitive on every platform.
  `ZoneInfo(name)` alone would also accept `america/new_york` on macOS's case-insensitive
  filesystem and not on Linux.
- **No setting**: periods use the system's local rules, through
  `datetime.astimezone(None)`. It applies the C library's `localtime()` to each moment, so
  daylight-saving changes are handled per transaction (checked: 2026-11-01 03:30Z → 23:30
  EDT, 07:30Z → 02:30 EST, with `TZ=America/New_York`).

**Rationale**:
- The stdlib has no portable way to get the system's IANA zone name. `astimezone(None)`
  doesn't need one, and it converts correctly.
- Keeping the type `ZoneInfo | None` lets one conversion, `moment.astimezone(zone)`, serve
  both cases.
- Loading a zone reads the system's time zone files, which is I/O, so it lives in a primitive
  (constitution IV) and `resolve_settings` stays pure.

**Testing**: tests that rely on the system zone set `TZ` and call `time.tzset()` in a fixture,
restoring both afterwards (POSIX, which matches the target platforms). Most tests pass an
explicit `ZoneInfo`.

**Alternatives considered**:
- The `tzlocal` package: it gives the system's zone name, but it's a new dependency for
  something `astimezone(None)` already handles.
- A fixed UTC offset from `datetime.now().astimezone()`: wrong across daylight-saving
  changes.
- Defaulting to UTC: contradicts FR-005.
- No `tzdata` package: macOS and Linux ship the database in `/usr/share/zoneinfo`, which is on
  `zoneinfo.TZPATH`.

## R3. Periods and ranges

**Decision**:
- **Today**: the run's clock (`clock()`, UTC-aware) converted to the summary time zone. This
  is computed once, so all three summaries agree (Assumptions: current moment).
- **Weeks**: the Monday of today's ISO week, and the 25 Mondays before it. Each week is
  labeled `f"{iso.year}-W{iso.week:02d}"` from `date.isocalendar()`. Stepping by 7 days
  handles 53-week years and year boundaries with no special cases.
- **Months**: today's month and the 11 before it, labeled `YYYY-MM`.
- **Years**: today's year and the 3 before it.
- **Each transaction's period**: from `datetime.fromtimestamp(occurred_at, UTC)
  .astimezone(zone).date()`. A transaction whose period isn't in the range is skipped. This
  covers both transactions older than the range and those dated after the current period
  (spec edge case).

**Rationale**: these are plain `date` arithmetic, all stdlib. Labels are the keys, so there is
one dictionary lookup per transaction per summary.

## R4. Exact sums, rounded once

**Decision**:
- **XMR**: an `int` sum of piconero.
- **USD**: each priced transaction's value is feature 002's exact `usd_value(amount, price)`.
  The values are added in a local `decimal` context with `prec = MAX_PREC` and `Inexact`
  trapped, so the sum is exact or the code raises; it never silently rounds.
- **Totals**: the exact period sums are added the same way.
- **Rounding**: only at display, with feature 003's `round_cents` (`ROUND_HALF_UP`). For
  values ≥ 0 that is the spec's "half a cent away from zero".

**Rationale**:
- The default context's 28 digits would round sums of 35-digit products.
- libmpdec sizes each result by its actual digits, so `MAX_PREC` costs nothing: 100,000
  additions took 5 ms in a check.
- Reusing `usd_value` and `round_cents` keeps one definition of "the value" and "rounded"
  across the export and the summaries.

**Alternatives considered**: scaled-integer arithmetic. It is exact too, but it would need a
common scale across prices with different numbers of decimals; `Decimal` already handles
that.

## R5. Number formatting

**Decision**:
- **XMR**: `f"{whole:,}.{fraction:012d}"` from `divmod(piconero, 10**12)`, so the grouping
  comes from integer formatting and the 12 decimals are never grouped (clarification Q3).
- **USD**: `"$" + format(round_cents(value), ",f")`. `Decimal.__format__` supports `,`
  grouping without going through `float`.

Both are independent of the locale: Python's `,` format option always uses `,` and `.`
(Assumptions: number format).

## R6. Marks and legend

**Decision**:
- **Marks**: `*` when a figure includes a provisional price, `?` when it leaves out an
  unpriced transaction, and `*?` when both apply. They follow the USD figure, separated by a
  space.
- **Mark suffix**: marks are part of the USD cell. If any row in a table has a mark, every
  USD cell in that table gets a space and its marks padded to the longest mark in the table,
  so the right-justified figures stay aligned. There is no separate mark column, so the box
  drawing has no extra border for one.
- **Legend**: after all the summaries, one blank line, then one line per mark that appears,
  `*` first:

  ```text
  * includes a provisional price, which may still change
  ? leaves out transactions that have no price yet
  ```

**Rationale**:
- Both marks are plain ASCII (Assumptions), and both are easy to read next to a number.
- `*` is the usual footnote mark.
- `?` suggests "incomplete" without implying a wrong figure.

**Alternatives considered**:
- `†`/`‡`: not ASCII.
- Letters (`p`, `u`): easy to misread as part of the figure.

## R7. Tables and layout with rich

**Decision**: the tables and the side-by-side layout are built with rich, as in the original
tool. rich becomes a direct dependency (`rich>=15.0.0` in `pyproject.toml`). It was already
installed as Typer's dependency, at 15.0.0 in `uv.lock`.

- **One table**: `Table(title=<title>, box=box.ROUNDED, header_style="bold")`, the original
  tool's style.
  - Columns `Period` (left), `XMR` (right), and `USD` (right), each `no_wrap=True`.
  - The period rows come first, then `table.add_section()` and the `Total` row, so a rule
    separates the total.
  - Every cell is a `Text`, so nothing is parsed as markup.
  - rich's defaults stand for everything not named here: the title is centered above the
    table in the `table.title` style, and cells have one space of padding.
- **Side by side**: a `Table.grid(padding=(0, 4, 0, 0))` with two columns. The weekly table
  is on the left. On the right is `Group(monthly, Text(""), annual)`.
- **One after another**: `Group(weekly, Text(""), monthly, Text(""), annual)`.
- **Legend**: appended to either layout as `Text("")` and one `Text` per mark that appears.
- **Widths**: each table's width is `Measurement.get(...).maximum`, measured on a probe
  `Console(width=10_000)`.
  - `side_by_side_width = weekly + 4 + max(monthly, annual)`.
  - `sequential_width = max(weekly, monthly, annual)`.
  - Side by side is used when a terminal width is given and is at least
    `side_by_side_width`. Otherwise the tables go one after another.
- **Rendering**: `render_text(summaries, width, styled)` prints the chosen renderable into an
  in-memory `Console` and returns the captured text. The settings that make the output
  deterministic are:
  - `file=io.StringIO()`;
  - `width=max(width or 0, needed width)`, where the needed width is the layout's width or
    the longest legend line shown, whichever is larger;
  - `color_system="standard" if styled else None`;
  - `force_terminal=styled`;
  - `highlight=False`, `markup=False`, `emoji=False`, `legacy_windows=False`.

  The in-memory console is pure: it writes to memory only (constitution IV). The CLI echoes
  the text.
- **The CLI's part**: `width = shutil.get_terminal_size().columns` and `styled=True` only
  when `sys.stdout.isatty()`. Otherwise `width=None` and `styled=False`, which gives plain
  text with no ANSI codes in files and pipes.
- **Placement**: one blank line after the export line, then the summaries (or the
  no-transactions message), then the legend.

**Rationale**:
- **Style**: `box.ROUNDED` with a `bold` header matches the original tool (user decision,
  2026-10-27). The marks stay ASCII. The box-drawing characters are Unicode, so the
  contract's earlier "every character is ASCII" rule is dropped. Bold is not a color, so the
  spec's "colors are out of scope" still holds.
- **Never a console narrower than the layout**: rich shrinks columns and truncates figures
  with `…` when the console is narrower than a table. A prototype showed `0.250000000…` at
  width 30. Giving the console at least the needed width means a narrow terminal soft-wraps
  long lines and never shortens a figure (spec edge case: "no figure is shortened or
  dropped").
- **`highlight=False`**: rich's default highlighter would color numbers on a terminal, which
  would add color the spec doesn't ask for.
- **Determinism**: an explicit width, no color system, and no terminal detection make the
  captured text depend only on the summaries and the width, which is what golden files need.
  The CLI's own console settings only add bold and the title style on a real terminal.
- **Height**: side by side, the weekly table is 32 lines (title, top border, header, rule, 26
  rows, rule, total, bottom border). With the legend, the prototype output is 36 lines
  (SC-006: ≤ 40).
- **Width**: the contract example needs 103 columns side by side (prototype: side by side at
  103, one after another at 102). One after another, it needs 54: the tables need 50, but the
  legend's `*` line is 54 characters, and rich would wrap it at 50. The borders and padding
  add about 6 columns per table compared with plain text, so a typical wallet needs about 95
  columns, and an 80-column terminal gets the one-after-another layout.
- **Layers**: orchestration builds and renders (pure), and the CLI measures the terminal and
  prints text (presentation, constitution II). Both layers may import rich; it is a
  third-party library, outside the import-linter layers.

**Alternatives considered**:
- Hand-built plain-text tables: no dependency, but they don't match the original tool. This
  replaces the earlier plan.
- rich's `Columns` for the side-by-side layout: it wraps renderables to fit the console, so
  the threshold would be rich's and not *W*. An explicit grid makes the threshold testable.
- Printing straight to a `Console(file=sys.stdout)` in the CLI: a failure partway would leave
  part of a table on screen (FR-018). Rendering to text first and echoing it once avoids that.
- Typer's own terminal size helper: deprecated in Click. `shutil.get_terminal_size()` also
  honors `COLUMNS`, which helps when checking by hand.

## R8. What `run()` returns

**Decision**:
- `RunResult` gains `summaries: IncomeSummaries | None = None`. Every successful `run()` sets
  it, and `None` remains only as the default, so existing test constructions keep working.
- `IncomeSummaries` holds three `Summary` values and `transactions`, the count of all recorded
  transactions. When `transactions` is 0, the renderer shows the no-transactions message
  (FR-016).
- The figures are exact `Decimal`s and `int`s. Formatting happens in the renderer.

**Rationale**: the same pattern as feature 003's `exported` field. Keeping exact values in
the result lets tests check sums without parsing text.

## R9. Golden files

**Decision**: new golden files in `tests/golden/`:
- **`summaries_side_by_side.txt`** and **`summaries_sequential.txt`**: rendered with
  `render_text(..., width=200, styled=False)` and `render_text(..., width=None,
  styled=False)` from one synthetic set of records, with clock `2026-10-27T15:00:00Z` and zone
  `America/New_York`. The set covers both marks, a 1,000+ XMR row, a period split by the local
  date, and an empty period.
- **`summaries_unmarked.txt`**: all final prices, so no mark suffix and no legend.
- **`summaries_empty.txt`**: the no-transactions message.

The tests render into a rich `Console` with an explicit width and no color system, so the
output doesn't depend on the test machine's terminal or environment. They compare the text
with trailing spaces stripped from each line. rich pads titles and grid cells with spaces,
and editors and git often strip trailing whitespace from committed files. The visible
characters, including every box-drawing character, are locked exactly.

A CLI test checks the blank line before the summaries and that they come after the export
line.

**Rationale**: the constitution locks report output with golden files. Rendering writes only
to memory, so the golden tests need no wallet, database, or terminal.

## R10. Guarding the summary step (FR-018)

**Decision**: the summary step has three stages, and a failure in any of them becomes one
clean error. The run prints features 001–003's lines (including the export line), then
`Error: …`, and exits 1. No summary line is printed, and the export is left as written.

| Stage | Where | Guarded failures |
|-------|-------|------------------|
| Reading | `run()`: `summary_reader(conn)` | `StorageReadError`, and any other `Exception` |
| Computing | `run()`: `build_summaries(records, today, zone)` | `SummaryDataError` (invariants below), and any other `Exception` |
| Rendering | `summary_text(result, export_path, width, styled)` in orchestration, called by the CLI | `SummaryDataError`, and any other `Exception` (including rich's) |

- **Invariants**: `build_summaries` checks every record and raises `SummaryDataError` naming
  the transaction id. The checks are:
  - `amount_piconero` is a non-negative `int`;
  - `occurred_at` is an `int` that converts to a date;
  - `usd_price` is `None` or a finite `Decimal` > 0;
  - `price_status` is `None` exactly when the price is, and otherwise `provisional` or
    `final`.

  `render_text` checks its input the same way: the period counts are 26, 12 and 4, XMR
  values are non-negative `int`s, and USD values are finite and non-negative `Decimal`s. So a
  malformed `IncomeSummaries` raises `SummaryDataError` instead of printing nonsense.
- **Error type**: `SummaryError(RunError)` carries `result: RunResult`, which holds the sync,
  pricing, import and export results with `summaries=None`. `run()` raises it for the reading
  and computing stages. `summary_text` raises it for the rendering stage.
- **Message**:

  ```text
  cannot show the income summaries: <reason>. The export was written to <path>; recorded transactions and prices were kept.
  ```

  `<reason>` depends on the failure:
  - `StorageReadError`: `cannot read database <db path>: <error>`;
  - `SummaryDataError`: its message, for example `unexpected data for transaction <txid>:
    invalid price`;
  - anything else: `unexpected <ExceptionType>: <error>`.

  No traceback is printed, and no secret appears (constitution, feature 001 rules).
- **No partial output**: the CLI calls `summary_text`, which renders the complete summaries
  into an in-memory rich `Console` (R7) and returns the text, before printing anything. It
  then prints, in order:
  - the warnings (as today);
  - features 001–003's lines;
  - then either a blank line and the summary text, or, if rendering failed, nothing more on
    stdout and the `Error:` line on stderr.
- **Not guarded**: `KeyboardInterrupt` is a `BaseException`, so it still propagates. Ctrl-C
  during the summary step exits 130 with feature 001's message and prints no lines.

**Rationale**:
- One error shape for all three stages keeps the CLI simple, and every stage testable at its
  own level.
- Catching `Exception` is deliberate here. The summaries are a read-only view built after the
  export, and an unexpected bug in them must not hide the fact that the export succeeded, or
  show a traceback.
- Carrying the result on the error lets the CLI print the earlier lines without `run()`
  knowing about output.

**Testing**: each stage gets a failure injected, and each test asserts four things:
1. stdout holds exactly features 001–003's lines, including `Exported …`, and no summary
   line;
2. stderr holds the single `Error: cannot show the income summaries: …` line;
3. the exit status is 1;
4. the export on disk is byte-identical to the one this run wrote. A run with the default
   reader writes the reference export to compare against.

The injected failures are:
- **Reading**: a `summary_reader` that raises `StorageReadError("invalid stored price 'abc'")`,
  as an unparseable stored price would, and one that raises `RuntimeError`.
- **Computing**: a `summary_reader` that returns records with a `NaN` price, a negative
  amount, and a status without a price.
- **Rendering**: an `IncomeSummaries` with a `NaN` USD value, and a weekly summary with 25
  periods (passed through a fake `RunResult` in CLI tests). Also a monkeypatched renderer
  that raises `RuntimeError`.

**Alternatives considered**:
- Returning the error in `RunResult`: it makes every caller check two places for failure.
  Raising is the existing pattern for run errors.
- Letting rendering errors reach the CLI's generic `unexpected …` handler: that loses the
  earlier lines and says nothing about the export.
