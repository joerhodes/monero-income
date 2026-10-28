---

description: "Task list for feature 004: on-screen income summaries"
---

# Tasks: On-Screen Income Summaries

**Input**: Design documents from `specs/004-income-summaries/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (summaries.md,
cli.md, config.md, run-api.md), quickstart.md

**Tests**: Included. Constitution v1.2.0 requires them: VII sets a 90% coverage floor, and the
Development Workflow section requires report output to be locked by golden-file tests. Write
each story's tests first and confirm they fail.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md
- Paths are relative to the repository root. Features 001–003's layout and conventions apply.

## Rules that apply to every task

- XMR is `int` piconero and USD `Decimal`; never `float`, including in tests (constitution
  III).
  - Sum USD only with `exact_sum` (research R4).
  - Round only at display, with feature 003's `round_cents` from
    `orchestration/export_format.py`.
  - Format `Decimal` with `format(...)`, never `str(...)`.
- `summary.py` and `summary_format.py` are pure: no I/O and no printing (constitution IV).
  Only `primitives/timezones.py` reads the time zone database.
- The CLI only measures the terminal and prints text it is given (constitution II).
- **rich** draws the tables and layouts (research R7):
  - `box.ROUNDED`, `header_style="bold"`, `Text` cells.
  - Always render into an in-memory `Console` with an explicit width, at least the layout's
    width, so no figure is ever truncated.
  - Tests use `styled=False`, so no ANSI codes appear and the output is deterministic.
  - Golden comparisons strip trailing spaces from each line (research R9).
- Tests write only under `tmp_path`; the autouse `isolated_home` fixture covers `~`
  (constitution V). Test data is synthetic.
- Figures, labels and marks are ASCII; only rich's box-drawing borders are Unicode
  (contracts/summaries.md). User-facing text never says "transfer(s)" (FR-021).
- Feature 003's export bytes don't change: `tests/golden/xmr_income*.csv` must keep passing
  untouched.
- **Shared test records**: build `ExportRecord`s with a helper
  `rec(moment: str, amount: int, price: str | None, status: str | None, txid: str = ...)`.
  `moment` is an ISO UTC string, converted to Unix seconds. `txid` defaults to a sha256 of a
  counter. Fix "today" to `date(2026, 10, 27)` and the zone to
  `ZoneInfo("America/New_York")` unless a task says otherwise.

---

## Phase 1: Setup

**Purpose**: Confirm the starting point

- [X] T001 On branch `004-income-summaries`, run `uv sync` and the five gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run lint-imports`, `uv run pytest`), and confirm they pass before any change. Confirm `pyproject.toml` lists `rich>=15.0.0` under `dependencies` and `uv.lock` resolves rich 15.0.0 (plan.md). It is already declared; it was installed before as Typer's dependency. No other new dependencies.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Types, errors, and the test fixture every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Create `src/monero_income/orchestration/summary.py`. Module docstring: "Pure aggregation of recorded transactions into weekly, monthly and annual income summaries. No I/O." Add these, all frozen dataclasses with field comments as in contracts/run-api.md:
  - **`SummaryDataError(Exception)`**: docstring "A record or summary breaks an invariant (FR-018)." Its message names the transaction id or the field, never amounts or secrets.
  - **`PeriodFigures`**: `label: str`, `piconero: int`, `usd: Decimal` (`# exact, unrounded; priced transactions only`), `provisional: bool`, `unpriced: bool`.
  - **`Summary`**: `title: str`, `periods: tuple[PeriodFigures, ...]`, `total: PeriodFigures`.
  - **`IncomeSummaries`**: `weekly: Summary`, `monthly: Summary`, `annual: Summary`, `transactions: int` (`# all recorded transactions; 0 → the message`).
  - **Constants**: `WEEKLY_TITLE = "Weekly Summary"`, `MONTHLY_TITLE = "Monthly Summary"`, `ANNUAL_TITLE = "Annual Summary"`, `WEEKS = 26`, `MONTHS = 12`, `YEARS = 4`, `TOTAL_LABEL = "Total"`.
  - **`summary_failure_message(reason: str, export_path: Path) -> str`**: `f"cannot show the income summaries: {reason}. The export was written to {export_path}; recorded transactions and prices were kept."`. It lives here, not in `summary_format.py`, because both `summary_format.py` (T012) and `run.py` (T013) use it, and `summary_format.py` imports `run.py`. Putting it in `summary_format.py` would make the two import each other.
- [X] T003 In `src/monero_income/orchestration/run.py`:
  - Add `summaries: IncomeSummaries | None = None` as the last field of `RunResult`, commented `# set by every successful run()`.
  - Add `class SummaryError(RunError)`, docstring "The summary step failed after the export was written (FR-018)." Its `__init__(self, message: str, result: RunResult)` stores `self.result`.

  Re-export `IncomeSummaries`, `Summary`, `PeriodFigures` and `SummaryError` from `src/monero_income/orchestration/__init__.py` and add them to `__all__`. Existing `RunResult(...)` constructions must keep compiling unchanged.
- [X] T004 [P] Add a `local_tz` fixture to `tests/conftest.py`. It is not autouse: it returns a function `set_tz(name: str) -> None` that sets `TZ` with `monkeypatch.setenv` and calls `time.tzset()`. On teardown it calls `time.tzset()` again after monkeypatch restores `TZ`, so later tests see the original zone (research R2). Add a one-line test of the fixture to `tests/unit/test_summary.py` (create the file): with `set_tz("America/New_York")`, `datetime(2026, 11, 1, 3, 30, tzinfo=UTC).astimezone(None).date() == date(2026, 10, 31)`.

**Checkpoint**: All existing tests still pass; `uv run mypy` and `uv run lint-imports` are clean.

---

## Phase 3: User Story 1 - See recent income by week, month, and year after each run (Priority: P1) 🎯 MVP

**Goal**: Every successful run prints, after the export line, a blank line and the three
summaries one after another, in the machine's time zone. Each has exact sums rounded once,
zero rows for empty periods, and a total. With no transactions, one message is printed
instead. If the summary step fails anywhere, the run prints the earlier lines, then a clean
error, and exits 1 (FR-018).

**Independent Test**: Record transactions in three weeks of the current month and one two
years ago, all final-priced, and run with output redirected. After `Exported …` comes a blank
line, then weekly (26 rows + Total), monthly (12 + Total), and annual (4 + Total). Each row
matches its period's sum, empty periods show zero, and the totals match the periods shown.

### Tests for User Story 1 ⚠️ (write first, confirm they fail)

- [X] T005 [P] [US1] Add aggregation tests to `tests/unit/test_summary.py` (functions from T011):
  - **Labels and ranges**:
    - `week_labels(date(2026, 10, 27))` is `"2026-W19"` … `"2026-W44"` (26 labels);
    - `month_labels` gives `"2025-11"` … `"2026-10"`;
    - `year_labels` gives `["2023", "2024", "2025", "2026"]`;
    - a year boundary: `week_labels(date(2027, 1, 20))` ends `..., "2026-W53", "2027-W01", "2027-W02", "2027-W03"`;
    - `week_label(date(2027, 1, 1)) == "2026-W53"`;
    - `week_label(date(2026, 2, 9)) == "2026-W07"` (zero-padded).
  - **`local_date`**: `(ts("2026-11-01T03:30:00"), NY) → date(2026, 10, 31)`; `(ts("2026-10-26T03:30:00"), NY) → date(2026, 10, 25)`; with `zone=None` and `local_tz("UTC")`, `→ date(2026, 11, 1)`.
  - **`exact_sum`**: summing values that need more than 28 digits gives the exact result (compare with a hand-built `Decimal`); an empty iterable gives `Decimal(0)`.
  - **`build_summaries`**:
    - the spec's US1-5 month: 1.5 XMR at `150` final and 0.25 XMR at `160.004` final in 2026-05 gives `piconero == 1_750_000_000_000` and `usd == Decimal("265.001")` (exact, unrounded);
    - an unpriced record adds its piconero and leaves `usd` unchanged;
    - empty periods are `PeriodFigures(label, 0, Decimal(0), False, False)`;
    - a record older than the oldest shown period is in no row and no total, but is counted in `transactions`;
    - a record dated after today counts in nothing;
    - the US1-9 midnight cases (NY): `2026-11-01T03:30:00Z` → month `2026-10`, `2026-10-26T03:30:00Z` → week `2026-W43`;
    - both sides of the 2026-11-01 daylight-saving change (NY), with today `2026-11-10`: `2026-11-01T03:30:00Z` (23:30 EDT on 2026-10-31, before the change) → month `2026-10`, week `2026-W44`; `2026-11-02T04:30:00Z` (23:30 EST on 2026-11-01, after it) → month `2026-11`, week `2026-W44`. Also `local_date` gives `date(2026, 10, 31)` and `date(2026, 11, 1)` for them;
    - a week split across two months: records on `2026-08-31` and `2026-09-01` (both `2026-W36`, noon UTC) give one weekly row `2026-W36` holding both, and separate monthly rows `2026-08` and `2026-09` holding one each;
    - each total's `piconero`/`usd` equals the exact sum of its periods;
    - period counts are 26/12/4, oldest first, with titles from T002;
    - with no records, `transactions == 0` and every figure is zero.
  - **Record checks** (`check_record`, FR-018; quote research R10). Each case raises `SummaryDataError` whose message contains the txid:
    - "`amount_piconero` is a non-negative `int`": a negative amount;
    - "`usd_price` is `None` or a finite `Decimal` > 0": `Decimal("NaN")`, `Decimal("0")`, `Decimal("-1")`;
    - "`price_status` is `None` exactly when the price is": a status without a price, a price without a status, and the status `"settled"`.
- [X] T006 [P] [US1] Create `tests/unit/test_summary_format.py` for the US1 parts of T012. Render with `render_text(s, width, styled=False)`, and strip trailing spaces per line before comparing.
  - **`format_xmr_grouped`**: `0 → "0.000000000000"`, `1 → "0.000000000001"`, `1_750_000_000_000 → "1.750000000000"`, `1_234_500_000_000_000 → "1,234.500000000000"`, `10**21 → "1,000,000,000.000000000000"`.
  - **`format_usd`**: `Decimal(0) → "$0.00"`, `Decimal("265.001") → "$265.00"`, `Decimal("1234567.895") → "$1,234,567.90"` (half up, FR-010), `Decimal("0.125") → "$0.13"`, `Decimal("0.00000000015") → "$0.00"`.
  - **`summary_table`** for an unmarked summary:
    - it is a `rich.table.Table` with `box is box.ROUNDED`, `header_style == "bold"`, and the summary's title;
    - the columns are `Period`, `XMR`, `USD`, justified `left`, `right`, `right`, all `no_wrap`;
    - it has 27 rows for the weekly summary (26 periods + `Total`), with a section break before `Total`.
  - **Rendered unmarked table**:
    - line 0 is the centered title;
    - line 1 starts with `╭`, and the header line reads `│ Period   │ … XMR │ … USD │`;
    - then a `├` rule, one row per period, a `├` rule, the `Total` row, and a `╰` bottom border;
    - XMR and USD are right-aligned.
  - **No ANSI codes**: `render_text(s, None, styled=False)` contains no `\x1b`. With `styled=True`, the header line contains `\x1b[1m` (bold).
  - **No highlighting or markup**: with `styled=True`, the figure cells carry no color codes; only the bold header and the title style appear. A label containing `[bold]` prints literally (the cells are `Text`).
  - **Layout without marks**: `render_text(s, None, False)` is weekly, blank line, monthly, blank line, annual, with no legend.
  - **No truncation**: `render_text(s, 30, False)` still contains every figure in full (for example `1,234.500000000000`) and no `…`. The console width is at least the layout's width (research R7).
  - **No transactions**: an `IncomeSummaries` with `transactions == 0` renders `No transactions to summarize yet.\n`.
  - **Input checks** (research R10). Each raises `SummaryDataError`:
    - a weekly summary with 25 periods;
    - a negative `piconero`;
    - a `usd` of `Decimal("NaN")`;
    - a negative `usd`.
- [X] T007 [P] [US1] Create golden files and `tests/integration/test_summaries_golden.py` (research R9):
  - **`tests/golden/summaries_unmarked.txt`**: the sequential rendering (`width=None`) of `build_summaries` over synthetic records with **final prices only**. Today is 2026-10-27 in NY. Include: the US1-5 month (1.5 XMR at 150 and 0.25 XMR at 160.004 in 2026-05); a 1,234.5-XMR row at 152.345 in 2026-06 (188,069.9025); a record in 2025-03 that appears only in the annual summary; and a NY-midnight record at `2026-10-01T03:30:00Z`, which falls in September locally (2026-09-30 23:30) but October in UTC.
  - **`tests/golden/summaries_empty.txt`**: `No transactions to summarize yet.`
  - **The test**: `render_text(summaries, None, styled=False)`, compared with each file's text after stripping trailing spaces from every line on both sides (research R9).
  - **How to write them**: from contracts/summaries.md. The box-drawing layout follows the contract's example, which was produced by a rich prototype with exactly these settings; the figures are checked against the arithmetic in the contract's notes. The module docstring records this, as feature 003's `test_export_golden.py` does.
- [X] T008 [P] [US1] Create `tests/integration/test_summaries.py`. Reuse feature 003's pattern from `tests/integration/test_export.py`: `FakeWalletRpc`, `FakePriceSource`, and a `FakeClock` at `2026-10-27T15:00:00Z`. Use `local_tz("America/New_York")` with no `timezone` option. Cases:
  - **Summaries are set**: a successful `run()` returns `result.summaries`, and it equals `build_summaries(export_records(conn), date(2026, 10, 27), None)` read from the same database after the run (FR-019);
  - **Same data as the export**: the summaries' grand XMR total over the transactions in range equals the sum of the export's `xmr` column for the same transactions;
  - **No transactions**: an empty wallet gives `summaries.transactions == 0`;
  - **Failures before the export**: a sync failure, an invalid import file, and an export write failure (reports path is a file) each raise `RunError` that is **not** a `SummaryError`, with no summaries built (FR-001);
  - **Read-only**: the database's `total_changes` from the summary step is 0, and the export bytes equal what the export step wrote (FR-017).
- [X] T009 [P] [US1] Create `tests/integration/test_summary_failures.py` for the reading and computing stages (FR-018, research R10). Each case first runs once with the default reader to get the reference export bytes. It then runs with the injected `summary_reader` and asserts:
  - (a) `run()` raises `SummaryError`;
  - (b) `error.result.exported` is set and `error.result.summaries is None`;
  - (c) `str(error)` starts with `cannot show the income summaries: ` and contains `The export was written to <absolute export path>; recorded transactions and prices were kept.`;
  - (d) the export on disk is byte-identical to the export this run wrote;
  - (e) the recorded transactions and prices are unchanged.

  The cases are:
  - **Reading**: a reader raising `StorageReadError("invalid stored price 'abc'")`. The reason is `cannot read database <db path>: invalid stored price 'abc'`.
  - **Reading**: a reader raising `RuntimeError("boom")`. The reason is `unexpected RuntimeError: boom`.
  - **Computing** (unexpected data): a reader returning one record with a `Decimal("NaN")` price, one with a negative amount, and one with `price_status="final"` and no price. Each reason is the `SummaryDataError` message naming the txid.
  - **Not guarded**: a reader raising `KeyboardInterrupt`. It propagates and is not turned into a `SummaryError`.
- [X] T010 [P] [US1] Add CLI tests:
  - **In `tests/cli/test_cli_success.py`**: extend `FakeRun` with an optional `summaries: IncomeSummaries | None`. A `FakeRun` that sets `summaries` also sets `exported`, as `run()` does (T014 passes `exported.path` to `summary_text`). Then:
    - with summaries, stdout is features 001–003's lines, then `""`, then exactly `render_text(summaries, None, styled=False)`, with no ANSI codes (`CliRunner` isn't a terminal);
    - with `transactions == 0`, the line after `""` is `No transactions to summarize yet.`;
    - with `summaries=None`, the output is unchanged from feature 003.
  - **In `tests/cli/test_cli_errors.py`** (FR-018):
    - `run` raising `SummaryError(message, result)`, where `result` has `recorded=2` and an `exported` path: stdout is exactly the `_summary_lines(result)` lines, ending with `Exported …`, with no blank line after them; stderr is `Error: <message>`; exit 1;
    - a rendering failure: a `FakeRun` with an `exported` path and summaries whose weekly summary has 25 periods. The same assertions hold, with the message starting `cannot show the income summaries: unexpected data`, and stdout has no table line;
    - a renderer patched to raise `RuntimeError("boom")` (monkeypatch `render_text` in `monero_income.orchestration.summary_format`): message `… unexpected RuntimeError: boom. The export was written to …`; exit 1;
    - in all three, no `Traceback` appears in the output.

### Implementation for User Story 1

- [X] T011 [US1] Complete `src/monero_income/orchestration/summary.py` (data-model.md, research R3, R4, R10):
  - **`local_date(occurred_at: int, zone: ZoneInfo | None) -> date`**: `datetime.fromtimestamp(occurred_at, UTC).astimezone(zone).date()`.
  - **Labels**:
    - `week_label(d)`: `f"{iso.year}-W{iso.week:02d}"`;
    - `month_label(d)`: `f"{d.year}-{d.month:02d}"`;
    - `year_label(d)`: `f"{d.year}"`.
  - **Ranges, each oldest first**:
    - `week_labels(today)`: Monday of today's week minus 25…0 weeks, as week labels;
    - `month_labels(today)`: 12 months ending with today's;
    - `year_labels(today)`: 4 years ending with today's.
  - **`exact_sum(values: Iterable[Decimal]) -> Decimal`**: in `localcontext()` with `prec = MAX_PREC` and `traps[Inexact] = True`, start from `Decimal(0)`.
  - **`check_record(record: ExportRecord) -> None`**: raise `SummaryDataError(f"unexpected data for transaction {txid}: <field> …")` unless:
    - `amount_piconero` is an `int` (not `bool`) ≥ 0;
    - `occurred_at` is an `int` and `local_date` succeeds (`OverflowError`/`OSError`/`ValueError` → `SummaryDataError`);
    - `usd_price` is `None` or a finite `Decimal` > 0;
    - `price_status` is `None` exactly when `usd_price` is, and otherwise in `("provisional", "final")`.

    Use the words `invalid amount`, `invalid moment`, `invalid price`, `invalid price status`.
  - **`summarize(records, labels, label_of, title) -> Summary`**:
    - one pass;
    - a dict from label to running piconero and a list of exact USD values;
    - records whose label isn't in `labels` are skipped;
    - unpriced records add piconero only;
    - USD per period is `exact_sum` of `usd_value(amount, price)` (reuse `orchestration/valuation.py`);
    - for US1, set `provisional=False, unpriced=False` everywhere (US2 fills them in);
    - the total is `exact_sum` over the periods' USD and the `int` sum of their piconero.
  - **`build_summaries(records: Sequence[ExportRecord], today: date, zone: ZoneInfo | None) -> IncomeSummaries`**: call `check_record` on every record first. Then compute each record's local date once and build the weekly, monthly and annual summaries. `transactions=len(records)`.
- [X] T012 [US1] Create `src/monero_income/orchestration/summary_format.py` (contracts/summaries.md, research R5, R7). It builds rich renderables and renders them only into an in-memory `Console`. Its module docstring is the contract's first paragraph.
  - **Constants**: `NO_TRANSACTIONS = "No transactions to summarize yet."`; `TABLE_GAP = 4`; `PROBE_WIDTH = 10_000`.
  - **`format_xmr_grouped(piconero: int) -> str`**: `whole, fraction = divmod(piconero, 10**12)`; `f"{whole:,}.{fraction:012d}"`.
  - **`format_usd(value: Decimal) -> str`**: `"$" + format(round_cents(value), ",f")`, with `round_cents` imported from `orchestration/export_format.py`.
  - **`check_summaries(s: IncomeSummaries) -> None`**: raise `SummaryDataError` unless:
    - the period counts are `WEEKS`/`MONTHS`/`YEARS`;
    - every `piconero` is an `int` ≥ 0;
    - every `usd` is a finite `Decimal` ≥ 0.

    Name the summary and label in the message.
  - **`summary_table(summary: Summary) -> Table`**:
    - `Table(title=summary.title, box=box.ROUNDED, header_style="bold")`;
    - columns `Period` (`justify="left"`), `XMR` (`justify="right"`) and `USD` (`justify="right"`), all `no_wrap=True`;
    - one `add_row(Text(label), Text(format_xmr_grouped(...)), Text(format_usd(...)))` per period;
    - then `table.add_section()` and the `Total` row;
    - no marks yet (US2);
    - leave every other `Table` option at rich's default.
  - **`table_width(table: Table) -> int`**: `Measurement.get(probe, probe.options, table).maximum` with `probe = Console(width=PROBE_WIDTH, file=io.StringIO())`.
  - **`summary_renderable(summaries: IncomeSummaries, width: int | None) -> tuple[RenderableType, int]`**:
    - if `transactions == 0`, return `(Text(NO_TRANSACTIONS), len(NO_TRANSACTIONS))`;
    - otherwise return `(Group(weekly, Text(""), monthly, Text(""), annual), max of the three table widths)`;
    - ignore `width` for now (US3).
  - **`render_text(summaries: IncomeSummaries, width: int | None, styled: bool) -> str`**:
    1. `check_summaries`.
    2. `renderable, needed = summary_renderable(summaries, width)`.
    3. Print it into `Console(file=io.StringIO(), width=max(width or 0, needed), color_system="standard" if styled else None, force_terminal=styled, highlight=False, markup=False, emoji=False, legacy_windows=False)`.
    4. Return the buffer's text.
  - **`summary_text(result: RunResult, export_path: Path, width: int | None, styled: bool) -> str`**:
    - `export_path` is the export the run wrote, passed in by the CLI, so this function never reads the optional `result.exported` and needs no runtime check;
    - if `result.summaries is None`, return `""`;
    - otherwise return the complete `render_text(...)` text;
    - on any `Exception` (not `BaseException`), raise `SummaryError(summary_failure_message(reason, export_path), result)`, where `reason` is the `SummaryDataError` message or `f"unexpected {type(error).__name__}: {error}"`. `summary_failure_message` is imported from `summary.py` (T002).

  Re-export `render_text` and `summary_text` from `orchestration/__init__.py`.
- [X] T013 [US1] Wire the summary step into `run()` in `src/monero_income/orchestration/run.py` (contracts/run-api.md, research R1, R10):
  - **Seam**: add the keyword-only parameter `summary_reader: Callable[[sqlite3.Connection], Sequence[ExportRecord]] = export_records`.
  - **Zone**: `zone: ZoneInfo | None = None` for now (US4 sets it from settings). Compute `today = now().astimezone(zone).date()` once.
  - **Read**: right after `rows = read_export_rows(conn)` and before `conn.close()`, with no commit in between, so both reads share the implicit transaction's snapshot:

    ```python
    try:
        summary_records = summary_reader(conn)
    except Exception as error:
        summary_failure = error
    ```

  - **Order**: write the export exactly as today. Its failures are unchanged.
  - **Build**: then, if `summary_failure` is set, raise. Otherwise call `build_summaries(summary_records, today, zone)`, catching `Exception`. Either way, raise `SummaryError(summary_failure_message(reason, exported.path), partial)`, with `summary_failure_message` imported from `summary.py` (T002):
    - `partial` is the `RunResult` with `summaries=None`;
    - `reason` is `cannot read database {settings.db_path}: {error}` for a `StorageReadError`, the message for a `SummaryDataError`, and `unexpected {type(error).__name__}: {error}` otherwise.
  - **Scope of the catch**: these `except` clauses must not catch `KeyboardInterrupt`, and must sit outside the existing `except (StorageError, WalletError)` handler so a summary-read `StorageReadError` isn't mapped to feature 001's message.
  - **Result**: return `RunResult(..., exported=exported, summaries=summaries)`.
- [X] T014 [US1] Print the summaries in `src/monero_income/cli.py` `main_command` (contracts/cli.md):
  - **Catch**: `except SummaryError as error:` before `except RunError`. Print the price-stopped warning as now, then `_summary_lines(error.result)`, then `_fail(str(error), 1)`.
  - **Render first**: after a successful `run()`, `width = _terminal_width()`, then compute `text = summary_text(result, result.exported.path, width, styled=width is not None)` if `result.exported is not None`, else `text = ""`, **before printing anything**. `run()` always sets `exported` when it sets `summaries`, so the `else` branch shows no summaries rather than raising. On `SummaryError`, print the warning and `_summary_lines(result)`, then `_fail(str(error), 1)`.
  - **Print**: otherwise print the warning, the `_summary_lines(result)` lines, and, if `text`, `""` followed by `typer.echo(text, nl=False)`. The CLI never creates a rich `Console` for stdout itself, so a failure can't leave part of a table on screen.
  - **`_terminal_width() -> int | None`**: returns `None` for now (US3 fills it in).

  No other logic goes in the CLI.
- [X] T015 [US1] Run the full suite. Fix any existing test broken by `run()` now setting `RunResult.summaries`, for example a test asserting `result == RunResult(...)`, by adjusting its expectation (compare the fields it cares about, or include `summaries`). Don't disable the summary step.

**Checkpoint**: US1 works on its own. Redirected output shows the three summaries one after
another. Every FR-018 failure prints the earlier lines and one error, and exits 1.

---

## Phase 4: User Story 2 - Know which figures are incomplete or may change (Priority: P2)

**Goal**: USD figures that include a provisional price carry `*`, and those that leave out
an unpriced transaction carry `?`. Totals inherit their periods' marks, and a legend explains
the marks that appear.

**Independent Test**: A provisional-priced transaction this week, an unpriced one last
week, and a final-priced one earlier. This week shows `*`, last week `?`, the earlier week
neither; the totals show `*?`; the legend has both lines.

### Tests for User Story 2 ⚠️ (write first, confirm they fail)

- [ ] T016 [P] [US2] Add to `tests/unit/test_summary.py`:
  - a period with a provisional-priced record has `provisional=True`;
  - one with an unpriced record has `unpriced=True` and `usd` excluding it;
  - one with both has both;
  - a period whose records are all unpriced has `usd == Decimal(0)` and `unpriced=True`;
  - a final-only period has neither;
  - each total's flags are the `any` of its periods' flags, and a flagged record outside the range doesn't flag the total (FR-012, US2-1 to US2-5, US2-7).
- [ ] T017 [P] [US2] Add to `tests/unit/test_summary_format.py`:
  - **`marks`**: `""`, `"*"`, `"?"`, `"*?"` for the four flag combinations;
  - **Mark suffix**: in a table where any row has a mark, every USD cell is `format_usd(...) + " " + marks.ljust(longest)`, blank-padded for unmarked rows, so the rendered figures stay right-aligned. The table has no fourth column;
  - **No marks**: a table with no marks renders exactly as in US1;
  - **Legend**: after the layout, `Text("")` and then only the legend lines for marks that appear, `*` first, with the exact texts from contracts/summaries.md; there is no legend when no mark appears (US2-6). With `width=None`, each legend line is one rendered line, not wrapped, and the needed width is at least 54.
- [ ] T018 [P] [US2] Add `tests/golden/summaries_sequential.txt`: `render_text(..., None, styled=False)` of the contract's example records (contracts/summaries.md, Example), today 2026-10-27, NY. It is the contract's one-after-another example. Add it to `tests/integration/test_summaries_golden.py`, comparing with trailing spaces stripped per line.
### Implementation for User Story 2

- [ ] T019 [US2] In `src/monero_income/orchestration/summary.py` `summarize`, set `provisional` when any counted record has `price_status == "provisional"` and `unpriced` when any counted record has no price. Set the total's flags to the `any` of the periods' flags.
- [ ] T020 [US2] In `src/monero_income/orchestration/summary_format.py`:
  - add `marks(figures: PeriodFigures) -> str` (`"*"` if provisional, then `"?"` if unpriced);
  - in `summary_table`, append the mark suffix to the USD cell text as in T017;
  - add `LEGEND: dict[str, str]` with the contract's two lines;
  - in `summary_renderable`, append `Text("")` and one `Text(line)` per mark that appears, in `"*?"` order, to either layout, and return `max(layout width, longest legend line shown)` as the needed width. The `*` line is 54 characters, wider than the one-after-another layout's 50, and rich would wrap it at 50.
**Checkpoint**: US1 and US2 work; both golden files pass.

---

## Phase 5: User Story 3 - See all three summaries at once on a wide terminal (Priority: P2)

**Goal**: On a terminal at least *W* columns wide, weekly is shown on the left, with monthly
above annual on the right. Otherwise, and whenever the output isn't a terminal, the summaries
are shown one after another.

**Independent Test**: Render the contract example at width 200, at *W*, at *W* − 1, and with
`None`. The first two are side by side and the last two one after another, with identical
figures.

### Tests for User Story 3 ⚠️ (write first, confirm they fail)

- [ ] T021 [P] [US3] Add to `tests/unit/test_summary_format.py`:
  - **Threshold**: `side_by_side_width(summaries) == table_width(weekly) + 4 + max(table_width(monthly), table_width(annual))`. `render_text` at that width is side by side, and at width − 1 it is one after another (US3-1, US3-2). For the contract example the width is 103.
  - **`width=None`** is always one after another (US3-3).
  - **Side-by-side shape**:
    - the first border line starts with `╭` and contains a second `╭` at column weekly width + 4;
    - the annual table's title is centered over the right column, one blank line below the monthly table's `╰` border;
    - lines after the right side ends hold only the weekly table.
  - **Line limits**: no line, with trailing spaces stripped, is longer than the width given (US3-4). The side-by-side output is at most 40 lines (SC-006).
  - **Same content**: every period row's text (`│ label │ xmr │ usd │`) and the legend appear identically in both layouts (US3-5, FR-015).
- [ ] T022 [P] [US3] Add `tests/golden/summaries_side_by_side.txt` with the contract's side-by-side example, copied from contracts/summaries.md. Add a test to `tests/integration/test_summaries_golden.py` rendering the example records with `render_text(..., 200, styled=False)` and comparing with trailing spaces stripped per line.
- [ ] T023 [P] [US3] Add to `tests/cli/test_cli_success.py`:
  - **Wide terminal**: with `cli._terminal_width` monkeypatched to return 200, stdout after `""` equals `render_text(summaries, 200, styled=True)`, so it is side by side with ANSI bold headers;
  - **Narrow terminal**: with it returning 60, stdout equals `render_text(summaries, 60, styled=True)`, which is one after another;
  - **Not a terminal**: with it returning `None`, there are no ANSI codes;
  - **`_terminal_width` itself**: with `sys.stdout.isatty` patched to `False` it returns `None`; with it patched to `True` and `COLUMNS=123`, it returns `123`.
### Implementation for User Story 3

- [ ] T024 [US3] In `src/monero_income/orchestration/summary_format.py`:
  - add `side_by_side_width(summaries) -> int`;
  - in `summary_renderable`, when `width is not None and width >= side_by_side_width(...)`, build the side-by-side layout:
    - `grid = Table.grid(padding=(0, TABLE_GAP, 0, 0))` with two columns;
    - `grid.add_row(weekly, Group(monthly, Text(""), annual))`;
    - return `(grid, side_by_side_width)`, with the legend appended as in T020 (research R7).
- [ ] T025 [US3] In `src/monero_income/cli.py`, implement `_terminal_width()`: `shutil.get_terminal_size().columns if sys.stdout.isatty() else None` (research R7). This is presentation only.

**Checkpoint**: All three golden files pass; a wide terminal shows the side-by-side layout.

---

## Phase 6: User Story 4 - Use a time zone other than the machine's (Priority: P3)

**Goal**: `--timezone`, then the `timezone` config key, then the machine's zone decides the
periods. Invalid values fail before syncing.

**Independent Test**: With `local_tz("UTC")` and a transaction at `2026-11-01T03:30:00Z`:
with no setting it counts in 2026-11; with `timezone = "America/New_York"` in the file it
counts in 2026-10; with the file still set and `--timezone UTC`, it counts in 2026-11.

### Tests for User Story 4 ⚠️ (write first, confirm they fail)

- [ ] T026 [P] [US4] Add to `tests/unit/test_settings.py` (contracts/config.md):
  - no setting gives `Settings.timezone is None`;
  - the file value is used;
  - the option overrides the file;
  - `""` and `"  "` from the option or the file → `invalid timezone: must not be empty`, checked before the default;
  - `timezone = 5` in the file → `invalid timezone in <path>: expected a string`;
  - `timezone` in the file produces no unknown-key warning.
- [ ] T027 [P] [US4] Create `tests/adapters/test_timezones.py` for `load_zone`:
  - `"America/New_York"` and `"UTC"` return a `ZoneInfo` with that key;
  - each of these raises `UnknownTimeZoneError` whose message is the name: `"Mars/Olympus_Mons"`, `"America"` (a directory), `"america/new_york"` (wrong case, rejected on every platform), `"../etc/passwd"`, and `"/etc/passwd"`.
- [ ] T028 [P] [US4] Create `tests/integration/test_summary_timezone.py` with `run()` cases:
  - the Independent Test above (US4-1 to US4-3), using `local_tz("UTC")` and a `FakeClock` at 2026-11-02;
  - `--timezone Mars/Olympus_Mons` raises `RunError("invalid timezone: unknown time zone 'Mars/Olympus_Mons'")` before syncing: the fake wallet records no calls, no database file is created, and no export is written (FR-006, US4-4);
  - a configured zone also decides "today": with the clock at `2026-11-01T03:30:00Z` and NY, the last monthly label is `2026-10`.
- [ ] T029 [P] [US4] Add to `tests/cli/test_cli_success.py`: `--timezone Europe/Berlin` maps onto `CliOptions(timezone="Europe/Berlin")`. Extend `test_options_map_onto_cli_options`; omitting the option gives `None`.

### Implementation for User Story 4

- [ ] T030 [P] [US4] Add `UnknownTimeZoneError(Exception)` to `src/monero_income/primitives/errors.py`, docstring "The time zone name isn't in the system's time zone database." Then create `src/monero_income/primitives/timezones.py` with `load_zone(name: str) -> ZoneInfo`. It returns `ZoneInfo(name)` only if `name in zoneinfo.available_timezones()`. Otherwise, or on `ZoneInfoNotFoundError`, `ValueError` or `OSError`, it raises `UnknownTimeZoneError(name)` (research R2).
- [ ] T031 [US4] Add the `timezone` setting to `src/monero_income/orchestration/settings.py` (contracts/config.md):
  - add `"timezone"` to `STRING_KEYS`;
  - add `timezone: str | None = None` to `CliOptions` and `Settings`;
  - in `resolve_settings`, `picked = _pick(options.timezone, file_values["timezone"])`; if `picked is not None and not picked.strip()`, raise `RunError("invalid timezone: must not be empty")`; set `Settings.timezone=picked`.

  Same pattern as `reports_path`, and no zone loading here (it stays pure).
- [ ] T032 [US4] In `src/monero_income/orchestration/run.py`, right after `resolve_settings` and before `connect`, set `zone = load_zone(settings.timezone) if settings.timezone is not None else None`. Map `UnknownTimeZoneError` to `RunError(f"invalid timezone: unknown time zone '{settings.timezone}'")`. Remove T013's temporary `zone = None`.
- [ ] T033 [US4] Add the `--timezone` option to `main_command` in `src/monero_income/cli.py`: `timezone: Annotated[str | None, typer.Option("--timezone", help="Time zone for the income summaries, e.g. America/New_York (default: this machine's).")] = None`. Place it after `--reports-path`, matching contracts/cli.md's usage block, and pass it into `CliOptions(timezone=timezone)`.

**Checkpoint**: All four stories work; the full suite is green.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T035 [P] Confirm the "transfer" scan in `tests/cli/test_messages.py` covers `orchestration/summary.py` and `orchestration/summary_format.py` (its `orchestration/*.py` glob), and that the new messages say "transaction(s)" (FR-021).
- [ ] T036 [P] Update `README.md`:
  - **Usage intro**: replace "Summaries come in a later feature." with a sentence saying every run ends with weekly, monthly and annual income summaries.
  - **Configure**: add `timezone = "America/New_York"   # optional; default: this machine's time zone` to the config example.
  - **Run**: add `[--timezone ZONE]` to the usage block after `[--reports-path DIR]`.
  - **"The summaries" subsection**:
    - the three ranges and that each includes the current period;
    - ISO week labels;
    - that periods follow the local or configured time zone, while prices stay by UTC day;
    - the `*`/`?` marks;
    - the two layouts, and that redirected output is always one after another;
    - a short excerpt from the contract example.
  - **Status table**: set 003's row to `Done` if it isn't already, and replace the `[004 …] Planned` row with `[004 Income summaries](specs/004-income-summaries/) | In Progress | Weekly, monthly and annual summaries on screen`.

  Don't change the Intro or "How I used AI" sections.
- [ ] T037 Run all five gates and fix failures until they pass with coverage ≥ 90%.
- [ ] T038 Run the manual checks in `specs/004-income-summaries/quickstart.md` against the real wallet and record the results in the PR description. Don't commit any output, database, or config file.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → stories → **Polish**.
- **Phase 2**: T002 and T004 in parallel; T003 after T002 (it imports the types).
- **US1 (Phase 3)**:
  - Tests T005–T010 in parallel first.
  - Then T011, then T012 (it imports `summary.py`'s types), then T013 (needs T011 and T012; `summary_failure_message` comes from T002), T014 (needs T012 and T013), and T015.
- **US2 (Phase 4)**: depends on US1's T011/T012. T016–T018 in parallel, then T019 and T020 (different files, so they can run in parallel).
- **US3 (Phase 5)**: depends on US1's T012 and T014. It is independent of US2, except that its golden file includes marks, so do it after US2 or accept the golden test failing until US2 lands. T021–T023 in parallel, then T024 and T025 (different files).
- **US4 (Phase 6)**: depends on Phase 2 and US1's T013. It is independent of US2 and US3. T026–T029 in parallel; T030 and T031 in parallel; then T032 (needs both) and T033.
- **Polish**: after the desired stories. T035 and T036 in parallel, then T037, then T038.

### Parallel Opportunities

- Phase 2: T002, T004.
- US1 tests: T005–T010 together (six files).
- US2: T016–T018 together; T019 and T020 together.
- US3: T021–T023 together; T024 and T025 together.
- US4: T026–T029 together; T030 and T031 together.
- After US1: US2 and US4 can go in parallel. US3 and US4 both touch `cli.py`, and US2 and US3 both touch `summary_format.py`, so coordinate those files.

---

## Parallel Example: User Story 1

```bash
# Tests first (all different files):
Task: "T005 tests/unit/test_summary.py"
Task: "T006 tests/unit/test_summary_format.py"
Task: "T007 tests/golden/summaries_{unmarked,empty}.txt + tests/integration/test_summaries_golden.py"
Task: "T008 tests/integration/test_summaries.py"
Task: "T009 tests/integration/test_summary_failures.py"
Task: "T010 tests/cli/test_cli_success.py and tests/cli/test_cli_errors.py additions"

# Then, in order (each builds on the last):
Task: "T011 src/monero_income/orchestration/summary.py"
Task: "T012 src/monero_income/orchestration/summary_format.py"
Task: "T013 src/monero_income/orchestration/run.py"
Task: "T014 src/monero_income/cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 → Phase 2 (types, `RunResult.summaries`, `SummaryError`, the `local_tz` fixture).
2. Phase 3 (US1): the three summaries one after another, in the machine's time zone, with the
   FR-018 safeguard, locked by the unmarked and empty golden files.
3. **Stop and validate**: quickstart steps 3, 4, 5, 10 and 11.

US1 already includes the whole FR-018 guard (reading, computing, rendering), so even the MVP
never prints a partial summary or a traceback.

### Incremental Delivery

US1 (summaries) → US2 (marks and legend; without them unpriced days silently lower USD) →
US3 (side-by-side layout) → US4 (time zone setting) → Polish.

---

## Notes

- **Golden files** lock the report output (constitution). Any later change to the summaries'
  text must be stated in a spec and update `tests/golden/summaries_*.txt` in the same change.
- **No schema change** and no migration: the summaries only read.
- **Broad `except Exception`** is allowed only in the summary step (T012's `summary_text`
  and T013's guarded read and build), as research R10 decides. Nowhere else.
- **Commits**: commit after each task or logical group; never commit `.db` files, real
  output, or `config.toml`.
