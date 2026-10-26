---

description: "Task list for feature 003: transaction CSV export"
---

# Tasks: Transaction CSV Export

**Input**: Design documents from `specs/003-transaction-csv-export/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (export-csv.md,
cli.md, config.md, run-api.md), quickstart.md

**Tests**: Included. Constitution v1.2.0 requires them: VII sets a 90% coverage floor, and the
Development Workflow section requires report output to be locked by golden-file tests. Write
each story's tests first and confirm they fail.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md
- Paths are relative to the repository root. Feature 001/002's layout and conventions apply.

## Rules that apply to every task

- Amounts are `int` piconero and prices `Decimal`; never `float`, including in tests
  (constitution III). Format `Decimal` with `format(value, "f")`, never `str(value)`
  (research R4).
- Functions that fetch or persist don't format or sort; formatting and ordering are pure
  functions in `orchestration/export_format.py` (constitution IV).
- Tests write only under `tmp_path`. The autouse `isolated_home` fixture in
  `tests/conftest.py` already points `HOME` there, so the default `~/reports` is safe
  (constitution V).
- Test data is synthetic. Never commit a real export, database, or `config.toml`.
- User-facing text never says "transfer(s)" (FR-025).
- The export never writes to the database (FR-024).

---

## Phase 1: Setup

**Purpose**: Confirm the starting point

- [X] T001 On branch `003-transaction-csv-export`, run `uv sync` and the five gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run lint-imports`, `uv run pytest`), and confirm they pass before any change. No new dependencies are needed (plan.md).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error type, models, settings, and result types that every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Add two errors to `src/monero_income/primitives/errors.py` (data-model.md):
  - `ExportWriteError(Exception)`, docstring "The export file couldn't be written; the previous export was left unchanged." Its message is the OS reason only (for example `Permission denied`); it never includes file contents.
  - `ExportLockUnsupportedError(ExportWriteError)`, docstring "The reports directory's filesystem doesn't support file locking." Its `__init__` takes no arguments and sets the fixed message `the filesystem doesn't support file locking (some network shares don't); write the export to a local directory and copy it` (FR-027, contracts/cli.md).
- [X] T003 [P] Add the frozen dataclass `ExportRecord` to `src/monero_income/primitives/models.py`, docstring "One recorded transaction with its UTC day's price, as read for the export." Fields, in order:
  - `txid: str`
  - `height: int`
  - `amount_piconero: int`
  - `occurred_at: int`, commented `# UTC Unix seconds`
  - `usd_price: Decimal | None`, commented `# None when the day has no recorded price`
  - `price_status: Literal["provisional", "final"] | None`

  `usd_price` and `price_status` are "both set or both `None`" (data-model.md).
- [X] T004 Add the `reports_path` setting to `src/monero_income/orchestration/settings.py` (contracts/config.md):
  - `DEFAULT_REPORTS_PATH = "~/reports"`.
  - Add `"reports_path"` to `STRING_KEYS`.
  - Add `reports_path: str | None = None` to `CliOptions` and `reports_path: Path = Path("~/reports")` to `Settings`. The field default is a placeholder; `resolve_settings` always sets it.
  - In `resolve_settings`:
    1. `picked = _pick(options.reports_path, file_values["reports_path"])`.
    2. If `picked is not None and not picked.strip()`, raise `RunError("invalid reports_path: must not be empty")`. Check this **before** applying the default, so `""` is an error and not silently the default (FR-022, `/speckit-analyze` I1).
    3. Then `reports_path = picked if picked is not None else DEFAULT_REPORTS_PATH`, and set `Settings.reports_path=Path(reports_path).expanduser()`.

  A non-string value in the file is already rejected by `_file_string` with `invalid reports_path in <config path>: expected a string` (FR-022). Use the same message shapes as `db_path`, but don't copy its `or DEFAULT_DB_PATH` pattern; leave `db_path`'s code unchanged (out of scope).
- [X] T005 Add unit tests for T004 to `tests/unit/test_settings.py`:
  - the default resolves to `<HOME>/reports`;
  - the file value is used;
  - the option overrides the file;
  - `~` is expanded;
  - `""` and `"  "` from the option or the file → `invalid reports_path: must not be empty`;
  - `reports_path = 5` in the file → `invalid reports_path in <path>: expected a string`;
  - `reports_path` in the file produces no unknown-key warning.
- [X] T006 Add the frozen dataclass `ExportSummary(path: Path, transactions: int)` to a new `src/monero_income/orchestration/export.py`. Add `exported: ExportSummary | None = None` as the last field of `RunResult` in `src/monero_income/orchestration/run.py`. Re-export `ExportSummary` from `src/monero_income/orchestration/__init__.py` and add it to `__all__` (contracts/run-api.md). Existing constructions of `RunResult` must keep compiling unchanged.

**Checkpoint**: All existing tests still pass; `uv run mypy` and `uv run lint-imports` are clean.

---

## Phase 3: User Story 1 - Export every recorded transaction after each run (Priority: P1) 🎯 MVP

**Goal**: Every run whose sync and pricing complete writes `~/reports/xmr_income.csv`: a header
and one exactly formatted row per transaction, oldest first. The run prints the `Exported …` line.

**Independent Test**: With three transactions on two UTC days, one day priced (final) and one
not, `run()` writes the file with the header and three rows in time order. The priced rows show
the price, `final`, and the rounded value; the unpriced row shows `TBD` three times.

### Tests for User Story 1 ⚠️ (write first, confirm they fail)

- [X] T007 [P] [US1] Create `tests/unit/test_export_format.py` for the pure functions in T013, using the contracts/export-csv.md example values:
  - **`format_xmr`**:
    - `1234567890123 → "1.234567890123"`;
    - `2_000_000_000_000 → "2.000000000000"`;
    - `1 → "0.000000000001"`;
    - `1_234_500_000_000_000 → "1234.500000000000"`.
  - **`format_timestamp`**: the Unix seconds for 2026-10-17 14:03:05 UTC → `"2026-10-17T14:03:05Z"`, and midnight → `T00:00:00Z`.
  - **`format_price`**:
    - `Decimal("152.3456") → "152.3456"`;
    - `Decimal("150") → "150"`;
    - `Decimal("1E+2") → "100"`;
    - `Decimal("163.40000000000001")` unchanged;
    - `None → "TBD"`.
  - **`format_usd_value`**:
    - `(1234567890123, Decimal("152.3456")) → "188.08"`;
    - `(1_000_000_000_000, Decimal("152.345")) → "152.35"` (half up);
    - `(1, Decimal("150")) → "0.00"`;
    - `(1_234_500_000_000_000, Decimal("150")) → "185175.00"`;
    - `(2_000_000_000_000, Decimal("163.40000000000001")) → "326.80"`;
    - `(amount, None) → "TBD"`;
    - a 12-digit-amount × 30-digit-price case that would overflow the default 28-digit context still returns a 2-decimal string.
  - **`export_rows`**:
    - sorts by `(occurred_at, height, txid)`, including two records in the same second (height breaks the tie), the same second and height (txid breaks it), and a higher height with an earlier timestamp (it comes first);
    - each row is a 7-tuple in `HEADER` order;
    - an unpriced record gives `("TBD", "TBD", "TBD")` in the last three columns.
  - **No exponent or separator**: over all the above outputs, no value matches `[eE]` (outside the txid) or contains `,`.
- [X] T008 [P] [US1] Create `tests/adapters/test_export_db.py` for `export_records`. Use a database from `open_database(tmp_path / "x.db")`, filled with `insert_records` and `upsert_price`/`insert_imported`. Cases:
  - a transaction on a final-priced day gets that `Decimal` and `"final"`;
  - one on a provisional day gets `"provisional"`;
  - one on an unpriced day gets `None, None`;
  - two transactions on one day share the price;
  - a price stored as `"150"` reads back as `Decimal("150")`, and `"163.40000000000001"` exactly;
  - an empty database gives `[]`;
  - the database is unchanged afterwards (`total_changes` is 0).
- [X] T009 [P] [US1] Create `tests/adapters/test_export_file.py` with the US1 cases for `write_export` (T015):
  - it writes the header and rows as LF-terminated, unquoted CSV, with a final `\n`;
  - it returns the absolute final path;
  - it creates a missing directory, including parents (FR-005);
  - a second call replaces the first file in full, with no old rows left (FR-006);
  - an empty row list writes the header only.
- [X] T010 [P] [US1] Create `tests/integration/test_export.py`. Reuse the `at()`/`price_run` pattern from `tests/integration/test_pricing.py` with `FakeWalletRpc`, `FakePriceSource`, and `FakeClock`. Cases:
  - **Independent test**: the scenario above; the file is at `<HOME>/reports/xmr_income.csv` and `result.exported == ExportSummary(path=<that absolute path>, transactions=3)`.
  - US1-5: a provisional day's rows show `provisional` and a value from that price.
  - US1-7: a price source that fails (`PriceUnavailableError`) still produces an export with `TBD` rows, and the run succeeds.
  - US1-8/FR-002: a wallet failure (`WalletUnreachableError`) raises `RunError` and writes no file; an existing export (pre-written bytes) is byte-for-byte unchanged.
  - US1-9: an invalid `--import-prices` file and a storage write error during pricing each raise `RunError`, and the existing export is unchanged.
  - US1-10: no transactions → the header only, `transactions=0`.
  - FR-020: the export reflects prices recorded in the same run.
  - SC-008: two runs with nothing new produce byte-identical files.
  - FR-024: the transactions and prices tables are identical before and after the export step (compare with `tests/integration/helpers.table` and a `SELECT * FROM daily_prices`).
- [X] T011 [P] [US1] Create golden files and `tests/integration/test_export_golden.py` (research R8, contracts/export-csv.md):
  - **Data**: build a synthetic database with `open_database`, `insert_records`, `upsert_price`, and `insert_imported`. Use txids from `hashlib.sha256(seed).hexdigest()` and fixed timestamps.
  - **Coverage**: final, provisional, and unpriced days; a half-cent value; a price stored as `150`; a long-precision price; a 1-piconero amount; a value over 100,000 USD; two transactions in the same second; and a later block with an earlier timestamp.
  - **Run**: call `run()` with an empty `FakeWalletRpc`, a `FakePriceSource` that answers `NoPrice` for everything (so the provisional price is kept and the unpriced day stays `TBD`), and a `FakeClock` inside the history period.
  - **Assert**: the file's bytes equal `tests/golden/xmr_income.csv`. A second test with an empty database compares against `tests/golden/xmr_income_empty.csv`.
  - **Golden file contents**: write them by hand from the contract rules, not by copying the implementation's output, and check each value against contracts/export-csv.md.
- [X] T012 [P] [US1] Add CLI tests to `tests/cli/test_cli_success.py`. Extend `FakeRun` with an optional `exported: ExportSummary | None`. Cases:
  - `exported=ExportSummary(Path("/x/reports/xmr_income.csv"), 1)` prints `Exported 1 transaction to /x/reports/xmr_income.csv.` as the last stdout line;
  - `0` and `1234` print `Exported 0 transactions …` and `Exported 1234 transactions …`, with no separators;
  - the line comes after every pricing line;
  - with `exported=None`, no `Exported` line is printed, so existing tests keep their exact output.

### Implementation for User Story 1

- [X] T013 [P] [US1] Create `src/monero_income/orchestration/export_format.py` (pure, no I/O; data-model.md and research R4):
  - `HEADER = ("txid", "height", "timestamp_utc", "xmr", "usd_price", "price_status", "usd_value")`.
  - `TBD = "TBD"`.
  - `format_timestamp(occurred_at: int) -> str`: `datetime.fromtimestamp(occurred_at, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")`.
  - `format_xmr(amount_piconero: int) -> str`: `f"{amount_piconero // 10**12}.{amount_piconero % 10**12:012d}"`.
  - `format_price(price: Decimal | None) -> str`: `format(price, "f")` or `TBD`.
  - `round_cents(value: Decimal) -> Decimal`: `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` inside `localcontext()`, with `prec` at least the value's digit count plus 3. Do **not** trap `Inexact` here; rounding is the point.
  - `format_usd_value(amount_piconero: int, price: Decimal | None) -> str`: `format(round_cents(usd_value(amount_piconero, price)), "f")` or `TBD`. Reuse `usd_value` from `orchestration/valuation.py`.
  - `export_rows(records: Sequence[ExportRecord]) -> list[tuple[str, str, str, str, str, str, str]]`: sort by `(occurred_at, height, txid)` (FR-010), then build each row in `HEADER` order. `price_status` is the stored status or `TBD`.
- [X] T014 [P] [US1] Create `src/monero_income/primitives/export_db.py` with `export_records(conn: sqlite3.Connection) -> list[ExportRecord]`. Run the read-only `LEFT JOIN` query from data-model.md (no `ORDER BY`; ordering is T013's job) and convert `usd_price` text with `Decimal(text)`. Raise `StorageReadError(str(error))` on `sqlite3.Error`, and also when a stored price isn't a finite positive `Decimal` (`decimal.InvalidOperation`, or ≤ 0). Module docstring: only reads, never writes (FR-024).
- [X] T015 [P] [US1] Create `src/monero_income/primitives/export_file.py` with `write_export(directory: Path, name: str, header: Sequence[str], rows: Iterable[Sequence[str]]) -> Path`, US1 version (research R1, R2, R5):
  1. `directory = directory.absolute()`; `directory.mkdir(parents=True, exist_ok=True)`.
  2. `fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{name}.", suffix=".tmp")`, which gives mode `0o600`.
  3. Open with `os.fdopen(fd, "w", encoding="utf-8", newline="")`. Write with `csv.writer(file, lineterminator="\n")`: the header, then the rows. Then `flush()` and `os.fsync()`.
  4. `os.replace(tmp, directory / name)`; return `directory / name`.

  T023 adds locking, cleanup, and error translation.
- [X] T016 [US1] Complete `src/monero_income/orchestration/export.py` (contracts/run-api.md):
  - `EXPORT_FILE_NAME = "xmr_income.csv"`.
  - `read_export_rows(conn) -> list[tuple[str, ...]]` returns `export_rows(export_records(conn))`.
  - `write_export_file(directory: Path, rows: Sequence[Sequence[str]]) -> ExportSummary` calls `write_export(directory, EXPORT_FILE_NAME, HEADER, rows)` and returns `ExportSummary(path=<returned path>, transactions=len(rows))`.

  Reading and writing stay separate so `run()` can close the database between them (research R6).
- [X] T017 [US1] Wire the export into `run()` in `src/monero_income/orchestration/run.py`:
  - Inside the `try` that holds the connection, after `price_days` and its `finally: _close(source)`, call `rows = read_export_rows(conn)`.
  - After `conn.close()`, call `exported = write_export_file(settings.reports_path, rows)`. This call goes outside the connection's `finally`, but still inside the outer `try` whose `except (StorageError, WalletError)` maps errors through `_run_error`.
  - Return `RunResult(..., exported=exported)`.
  - Update the `run()` docstring order to "sync, import (if asked), price, then export".

  Any earlier exception must prevent the write (FR-002).
- [X] T018 [US1] Print the export line in `src/monero_income/cli.py` `_summary_lines`: when `result.exported is not None`, append `f"Exported {n} {_plural(n, 'transaction')} to {result.exported.path}."` last (contracts/cli.md).
- [X] T019 [US1] Run the full test suite. Fix any existing test broken by runs now writing `<HOME>/reports/xmr_income.csv`, for example a test that lists `tmp_path` contents, by adjusting the test's expectations, not by disabling the export.

**Checkpoint**: US1 tests and the golden files pass; a normal run writes the export and prints the line.

---

## Phase 4: User Story 2 - Never leave a broken export (Priority: P1)

**Goal**: Replacing the export is all-or-nothing. Leftovers from killed runs are cleaned up,
the file is always owner-only, and a failed write fails the run with the previous export intact.

**Independent Test**: Write an export, then make the next write fail partway. The old file is
byte-for-byte unchanged, no temporary file remains, and the run exits 1 with the contract's
error message.

### Tests for User Story 2 ⚠️ (write first, confirm they fail)

- [X] T020 [P] [US2] Add to `tests/adapters/test_export_file.py`:
  - **Failure mid-write**: a `rows` iterable that yields two rows then raises `OSError(errno.ENOSPC, "No space left on device")`. `write_export` raises `ExportWriteError` whose message contains `No space left on device`. A previously written export is byte-for-byte unchanged, and no `.xmr_income.csv.*.tmp` file remains (US2-3, US2-4).
  - **Interrupt mid-write**: the same, but raising `KeyboardInterrupt`. It propagates unchanged (not wrapped), the old file is unchanged, and no temporary file remains (US2-2).
  - **No previous export**: either failure leaves no `xmr_income.csv` (US2-4).
  - **Stale temporary file**: plant `.xmr_income.csv.abc123.tmp` with junk bytes. After a successful write it is gone, and the directory holds only `xmr_income.csv` (US2-5, FR-007). An unrelated file in the directory, such as `notes.txt`, is left alone.
  - **Permissions**: the new file has `stat.S_IMODE(mode) == 0o600`, including when the previous export was `chmod 0o644` (US2-7, FR-026). During the write the temporary file is `0o600`: check it from inside the rows iterable by globbing the directory.
  - **Lock**: while a test holds `fcntl.flock(dir_fd, LOCK_EX | LOCK_NB)` on the directory, a `write_export` in a thread blocks, then completes once the lock is released. Use a short timeout and `threading.Event`, with no real sleeps beyond the join timeout.
  - **Directory problems**: the reports path is an existing regular file → `ExportWriteError` (`Not a directory` / `File exists`). A directory with mode `0o500` → `ExportWriteError` (`Permission denied`); skip this case when running as root (`os.geteuid() == 0`).
  - **Locking unsupported** (FR-027, US3-7): monkeypatch `monero_income.primitives.export_file.fcntl.flock` to raise `OSError(code, os.strerror(code))`, parametrized over `errno.ENOLCK`, `errno.ENOTSUP`, and `errno.EOPNOTSUPP`. Each case gives `ExportLockUnsupportedError` with exactly the message in contracts/cli.md. A pre-written export is byte-for-byte unchanged, and no temporary file is created. A different `flock` error, such as `errno.EBADF`, gives a plain `ExportWriteError`, not the subclass.
- [X] T021 [P] [US2] Create `tests/integration/test_export_failures.py`:
  - After a good run, a second `run()` with `CliOptions(reports_path=<path of a regular file>)` raises `RunError`, with the exact message `cannot write export <abs path>/xmr_income.csv: <reason>. Recorded transactions and prices were kept; the previous export was not changed.`, matched with a regex on `<reason>`. The transactions recorded by that run are in the database (US2-6, FR-008).
  - A run with `monero_income.orchestration.export.write_export` monkeypatched to raise `KeyboardInterrupt` propagates `KeyboardInterrupt`, the previous export is unchanged, and the run's recorded transactions are kept.
- [X] T022 [P] [US2] Add to `tests/cli/test_cli_errors.py`:
  - A `RunError` from the export prints `Error: cannot write export …` on stderr, exits 1, and prints nothing on stdout (contracts/cli.md: the sync and pricing lines aren't printed on failure).
  - `KeyboardInterrupt` still exits 130 with feature 001's message.

### Implementation for User Story 2

- [X] T023 [US2] Harden `write_export` in `src/monero_income/primitives/export_file.py` (research R1–R3, data-model.md):
  1. After `mkdir`, open the directory with `os.open(directory, os.O_RDONLY)` and take `fcntl.flock(dir_fd, fcntl.LOCK_EX)`. Hold the lock for the rest of the function and close `dir_fd` in a `finally`, which releases it.
  2. Under the lock, delete every `directory.glob(f".{name}.*.tmp")` entry (`missing_ok=True`).
  3. Write the temporary file as in T015, inside `try`. On **any** `BaseException`, unlink the temporary file (`missing_ok=True`) and re-raise.
  4. After `os.replace`, call `os.fsync(dir_fd)`.
  5. If `flock` raises `OSError` with `errno` in `{errno.ENOLCK, errno.ENOTSUP, errno.EOPNOTSUPP}`, raise `ExportLockUnsupportedError()` from it, before any temporary file is created (FR-027, research R3).
  6. Translate any other `OSError` from any step (mkdir, open, flock, write, fsync, replace) into `ExportWriteError(error.strerror or type(error).__name__)`, raised `from error`. Never translate `KeyboardInterrupt` or other non-`OSError` exceptions.
- [X] T024 [US2] In `src/monero_income/orchestration/run.py`, catch `ExportWriteError` around `write_export_file` and raise `RunError(f"cannot write export {settings.reports_path.absolute() / EXPORT_FILE_NAME}: {error}. Recorded transactions and prices were kept; the previous export was not changed.")` from it (FR-008, contracts/cli.md).

**Checkpoint**: US1 and US2 tests pass; failure and interrupt cases leave the previous export intact.

---

## Phase 5: User Story 3 - Choose where the export is written (Priority: P2)

**Goal**: `--reports-path` on the command line, `reports_path` in the config file, default `~/reports`.

**Independent Test**: Three runs: no setting (export in `<HOME>/reports`), config key only
(its directory), config key plus option (the option's directory).

### Tests for User Story 3 ⚠️ (write first, confirm they fail)

- [ ] T025 [P] [US3] Create `tests/integration/test_export_location.py` with `run()` cases (US3-1 to US3-6):
  - **US3-1**: the default writes `<HOME>/reports/xmr_income.csv`.
  - **US3-2**: a config file with `reports_path = "<tmp>/cfg-reports"` writes there.
  - **US3-3**: the config key plus `CliOptions(reports_path="<tmp>/opt-reports")` uses the option.
  - **US3-4**: a nested missing directory (`<tmp>/a/b/c`) is created.
  - **`~` expansion**: `reports_path = "~/elsewhere"` writes under `<HOME>/elsewhere`.
  - **Relative path**: `"rel"` resolves against the current directory (use `monkeypatch.chdir(tmp_path)`), and `ExportSummary.path` is absolute.
  - **US3-6**: `reports_path = 5`, `reports_path = ""` in the file, and `CliOptions(reports_path="")` each raise `RunError` before the wallet is contacted, and the fake wallet's call log is empty.
  - **US3-7**: with `fcntl.flock` in `monero_income.primitives.export_file` monkeypatched to raise `OSError(errno.ENOLCK, …)`, `run()` raises `RunError` with the message `cannot write export <abs path>: the filesystem doesn't support file locking (some network shares don't); write the export to a local directory and copy it. Recorded transactions and prices were kept; the previous export was not changed.`
- [ ] T026 [P] [US3] Add to `tests/cli/test_cli_success.py`: `--reports-path /x/y` maps onto `CliOptions(reports_path="/x/y")`, extending `test_options_map_onto_cli_options`, and omitting it gives `None`.

### Implementation for User Story 3

- [ ] T027 [US3] Add the `--reports-path` option to `main_command` in `src/monero_income/cli.py`: `reports_path: Annotated[str | None, typer.Option("--reports-path", help="Directory for the xmr_income.csv export (default ~/reports).")] = None`. Pass it into `CliOptions(reports_path=reports_path)`. Place it after `--db-path`, matching contracts/cli.md's usage line.

**Checkpoint**: All three ways of choosing the directory work; invalid config fails before syncing.

---

## Phase 6: User Story 4 - A reader who has never seen the tool can understand the export (Priority: P3)

**Goal**: Standalone reader documentation for an auditor (FR-023).

**Independent Test**: Using only `docs/export-csv.md` and a sample export, a reader can explain
every column and recompute any `usd_value`.

### Implementation for User Story 4

- [ ] T028 [P] [US4] Write `docs/export-csv.md` for a reader who has never seen the tool (research R9). Do not read or link `docs/sdd-log/`. Cover:
  - what the file is and when it's written (after each successful run; replaced in full; not written by a failed run);
  - one row per incoming transaction, oldest first by `timestamp_utc`, then block height, then txid;
  - a table of the seven columns, each with its meaning, format and units, taken from contracts/export-csv.md;
  - `TBD` (no price recorded yet, for any reason; a later export may fill it in), `provisional` (the day's price may still be refreshed until an hour after the UTC day ends), and `final` (never changes);
  - which UTC calendar day a price applies to;
  - the rounding rule with the worked example `1.000000000000 × 152.345 = 152.345 → 152.35`;
  - that `usd_value` is the only rounded column, and that all other values are exact;
  - that no value uses scientific notation or thousands separators;
  - a note that spreadsheets may display fewer decimals than the file holds, so check against the file's text;
  - a "Where the export can be written" note: the reports directory must be on a filesystem that supports file locking. Some network shares don't; there the run fails with a message saying so. To share the export, write it to a local directory and copy it (FR-027);
  - the six-row example from the contract, with placeholder txids.
- [ ] T029 [P] [US4] Update the Usage section of `README.md`:
  - **Configure**: add `reports_path = "~/reports"` to the config example.
  - **Run**: add `[--reports-path DIR]` to the usage block after `--db-path`, and the `Exported N transactions to …` line as the last line of the output example.
  - Add a short "The export" subsection: the file `xmr_income.csv`, owner-only permissions, replaced each run, and a link to `docs/export-csv.md`.
  - Replace the sentence "CSV output and summaries come in later features." with "Summaries come in a later feature."
  - In "The export" subsection, note that the reports directory must support file locking; for a network share that doesn't, write locally and copy (FR-027).

  Don't change the Intro, Status, or "How I used AI" sections. The Status table already lists 003 as the transaction export.
- [ ] T030 [US4] Cross-check `docs/export-csv.md` against `tests/golden/xmr_income.csv`: every value form in the golden file (`TBD`, a provisional row, a half-cent row, `150`, a long price, `0.00`) is explained in the document, and the document's example rows obey the contract.

**Checkpoint**: The documentation stands alone (SC-007).

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T031 [P] Confirm the "transfer" scan in `tests/cli/test_messages.py` covers the new modules (`orchestration/export.py` and `orchestration/export_format.py` match its glob), and that the new error and output text says "transaction(s)" (FR-025).
- [ ] T032 [P] Add a property-style test to `tests/unit/test_export_format.py` (SC-002, SC-003, FR-019). For a few hundred generated records (seeded `random.Random`, integer piconero up to 10¹⁸, prices built as `Decimal(f"{int}.{int}")`), parse each row back:
  - `int(xmr.replace(".", "")) == amount_piconero`;
  - `Decimal(usd_price) == price`, **and** the text itself: `usd_price == format(price, "f")`, since `Decimal` equality ignores trailing zeros (`/speckit-analyze` U2);
  - `timestamp_utc` → Unix seconds equals `occurred_at`;
  - `abs(Decimal(usd_value) - usd_value(amount, price)) <= Decimal("0.005")`.

  No new dependency (don't add hypothesis).
- [ ] T033 Run all five gates and fix failures until they pass with coverage ≥ 90%.
- [ ] T034 Run the manual checks in `specs/003-transaction-csv-export/quickstart.md` against the real wallet and record the results in the PR description. Don't commit the export, the database, or the config file.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → stories → **Polish**.
- **Phase 2**: T002, T003 and T004 in parallel; T005 after T004; T006 any time in the phase.
- **US1 (Phase 3)**:
  - Tests T007–T012 in parallel first.
  - Then T013, T014 and T015 in parallel.
  - Then T016 (needs T013–T015), T017 (needs T016), T018, and T019.
- **US2 (Phase 4)**: depends on US1 (it hardens `write_export` and extends `run()`). T020–T022 in parallel, then T023 → T024.
- **US3 (Phase 5)**: depends on Phase 2 (settings) and US1 (`run()` writes the export). It is independent of US2. T025 and T026 in parallel, then T027.
- **US4 (Phase 6)**: T028 and T029 can start after Phase 2 (they follow the contracts). T030 needs T011's golden file.
- **Polish**: after the desired stories.

### Parallel Opportunities

- Phase 2: T002, T003, T004, T006.
- US1 tests: T007–T012 together; US1 modules: T013–T015 together.
- After US1: US2, US3 and US4 can go in parallel. US2 and US3 both touch `run.py`/`cli.py` lightly, so coordinate those files.

---

## Parallel Example: User Story 1

```bash
# Tests first (all different files):
Task: "T007 tests/unit/test_export_format.py"
Task: "T008 tests/adapters/test_export_db.py"
Task: "T009 tests/adapters/test_export_file.py"
Task: "T010 tests/integration/test_export.py"
Task: "T011 tests/golden/ + tests/integration/test_export_golden.py"
Task: "T012 tests/cli/test_cli_success.py additions"

# Then the three new modules:
Task: "T013 src/monero_income/orchestration/export_format.py"
Task: "T014 src/monero_income/primitives/export_db.py"
Task: "T015 src/monero_income/primitives/export_file.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 → Phase 2 (settings and types; all feature 001/002 tests green).
2. Phase 3 (US1): the export is written after each run and locked by golden files.
3. **Stop and validate**: quickstart steps 1–6.

US1 already writes via temporary file and rename (T015), so even the MVP never truncates an
existing export in place. US2 adds the guarantees for failures, interrupts, killed runs, and
concurrent runs.

### Incremental Delivery

US1 (export) → US2 (all-or-nothing, owner-only, failure status; ship US1 and US2 together,
both P1) → US3 (`--reports-path`) → US4 (reader documentation) → Polish.

---

## Notes

- **Golden files** are new in this feature (constitution: report output is locked by golden
  files). Any later change to the export's bytes must be stated in a spec and update
  `tests/golden/` in the same change.
- **No schema change** and no migration: the export only reads.
- **Commits**: commit after each task or logical group; never commit `.db` files, real
  exports, or `config.toml`.
