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
- Reading twice costs one more query. 100,000 rows are well within SC-007.

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
- **Mark column**: if any row in a table has a mark, the table reserves a mark column as
  wide as its longest mark, so USD figures stay right-aligned.
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

## R7. Layout and the width check

**Decision**:
- **Table**: a title line, a header line, a dashed rule, the period rows, a rule, and the total
  row.
- **Columns**: Period (left-aligned), XMR and USD (right-aligned), two spaces apart, each as
  wide as its widest cell. Each table sizes its own columns, and every line of a table is
  padded to the table's width.
- **Side-by-side**:
  - The weekly table is on the left. Four spaces to its right are the monthly table, a blank
    line, then the annual table.
  - It is used when the output is a terminal and the terminal is at least `weekly width + 4 +
    max(monthly width, annual width)` columns wide.
  - Trailing spaces are stripped from every line.
- **One after another**: weekly, blank line, monthly, blank line, annual.
- **Where it's decided**: the CLI passes `width = shutil.get_terminal_size().columns` only when
  `sys.stdout.isatty()`, otherwise `None`. The pure renderer in orchestration decides the
  layout from that value.
- **Placement**: one blank line after the export line, then the summaries (or the
  no-transactions message), then the legend.

**Rationale**:
- **Layers**: the CLI only measures the terminal (presentation, constitution II). Layout and
  text are pure and golden-tested in orchestration, as with feature 003's `export_format`.
- **Height**: in the side-by-side layout the left table is 31 lines and the right side 27, so
  with the legend the output is at most 34 lines (SC-006: ≤ 40).
- **Width**: the prototype in the contract needs 97 columns, driven by a 1,234-XMR row.
  Typical payouts of a few XMR need about 85. An 80-column terminal therefore falls back to
  one after another; the spec accepts this.

**Alternatives considered**:
- Rich or another table library: a new dependency, and harder to lock in golden files.
- Typer's own terminal size helper: deprecated in Click. `shutil.get_terminal_size()` also
  honors `COLUMNS`, which helps when checking by hand.

## R8. What `run()` returns

**Decision**:
- `RunResult` gains `summaries: IncomeSummaries | None = None`. Every successful `run()` sets
  it, and `None` remains only as the default, so existing test constructions keep working.
- `IncomeSummaries` holds three `Summary` values and `transactions`, the count of all recorded
  transactions. When `transactions` is 0, the CLI prints the no-transactions message
  (FR-016).
- The figures are exact `Decimal`s and `int`s. Formatting happens in the renderer.

**Rationale**: the same pattern as feature 003's `exported` field. Keeping exact values in
the result lets tests check sums without parsing text.

## R9. Golden files

**Decision**: new golden files in `tests/golden/`:
- **`summaries_side_by_side.txt`** and **`summaries_sequential.txt`**: rendered from one
  synthetic set of records, with clock `2026-10-27T15:00:00Z`, zone `America/New_York`, and a
  width of 200 and `None`. The set covers both marks, a 1,000+ XMR row, a period split by the
  local date, and an empty period.
- **`summaries_unmarked.txt`**: all final prices, so no mark column and no legend.
- **`summaries_empty.txt`**: the no-transactions message.

They compare the renderer's lines joined with `\n`. A CLI test checks the blank line before
the summaries and that they come after the export line.

**Rationale**: the constitution locks report output with golden files. Rendering is pure, so
the golden tests need no wallet, database, or terminal.

## R10. Guarding the summary step (FR-018)

**Decision**: the summary step has three stages, and a failure in any of them becomes one
clean error. The run prints features 001–003's lines (including the export line), then
`Error: …`, and exits 1. No summary line is printed, and the export is left as written.

| Stage | Where | Guarded failures |
|-------|-------|------------------|
| Reading | `run()`: `summary_reader(conn)` | `StorageReadError`, and any other `Exception` |
| Computing | `run()`: `build_summaries(records, today, zone)` | `SummaryDataError` (invariants below), and any other `Exception` |
| Rendering | `summary_lines(result, width)` in orchestration, called by the CLI | `SummaryDataError`, and any other `Exception` |

- **Invariants**: `build_summaries` checks every record and raises `SummaryDataError` naming
  the transaction id. The checks are:
  - `amount_piconero` is a non-negative `int`;
  - `occurred_at` is an `int` that converts to a date;
  - `usd_price` is `None` or a finite `Decimal` > 0;
  - `price_status` is `None` exactly when the price is, and otherwise `provisional` or
    `final`.

  `render_summaries` checks its input the same way: the period counts are 26, 12 and 4, XMR
  values are non-negative `int`s, and USD values are finite and non-negative `Decimal`s. So a
  malformed `IncomeSummaries` raises `SummaryDataError` instead of printing nonsense.
- **Error type**: `SummaryError(RunError)` carries `result: RunResult`, which holds the sync,
  pricing, import and export results with `summaries=None`. `run()` raises it for the reading
  and computing stages. `summary_lines` raises it for the rendering stage.
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
- **No partial output**: the CLI renders the complete summary lines into a list before
  printing anything. It then prints, in order:
  - the warnings (as today);
  - features 001–003's lines;
  - then either a blank line and the summary lines, or, if rendering failed, nothing more
    on stdout and the `Error:` line on stderr.
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
