---

description: "Task list for feature 001: sync incoming wallet transactions"
---

# Tasks: Sync Incoming Wallet Transactions

**Input**: Design documents from `specs/001-sync-incoming-transactions/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md,
config.md, wallet-rpc.md, run-api.md), quickstart.md

**Tests**: Included. The spec doesn't request TDD explicitly, but constitution v1.2.0 requires
it in effect: VII requires pytest with a 90% coverage floor, and V requires every external
service to be faked behind a Protocol. Write each story's tests first and confirm they fail.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 from spec.md
- Paths are relative to the repository root (`src/` layout, see plan.md)

## Rules that apply to every task

- Amounts are `int` piconero everywhere; never `float` (constitution III). Parse JSON with
  stdlib `json`, which yields exact `int`.
- Functions that fetch or persist don't reshape; transformations do no I/O (constitution IV).
- Layering: `cli` imports only `orchestration`; `orchestration` imports `primitives`;
  `primitives` imports neither (constitution I, enforced by T002).
- Tests never use the network (pytest-socket) and never touch real user paths; the autouse
  fixture in `tests/conftest.py` (T005) points `HOME` at `tmp_path` (constitution V).
- Use in-memory SQLite only where a test calls `run()` at most once and doesn't inspect the
  database afterwards; `run()` closes its connection, which discards an in-memory database.
  Tests that call `run()` more than once or inspect the database after it use a `tmp_path`
  database file through the real `open_database`.
- No user-facing message contains the password or the word "transfer(s)" (FR-018, FR-019).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and quality gates

- [X] T001 Create `pyproject.toml` with `[project]` name `monero-income`, `requires-python = ">=3.13"`, runtime dependencies `typer` and `httpx`, a uv dev dependency group with `pytest`, `pytest-cov`, `pytest-socket`, `ruff`, `mypy`, `import-linter`, the uv build backend for a `src/` layout package `monero_income`, and `[project.scripts] monero-income = "monero_income.cli:main"`
- [X] T002 Add tool configuration to `pyproject.toml`:
  - ruff: lint rules plus formatter, line length 100.
  - mypy: `strict = true`, `files = ["src", "tests"]`.
  - pytest: `testpaths = ["tests"]`, `addopts = "--disable-socket --cov=monero_income --cov-report=term-missing --cov-fail-under=90"`.
  - import-linter `[tool.importlinter]` with `root_package = "monero_income"` and two contracts:
    - a `layers` contract `monero_income.cli` > `monero_income.orchestration` > `monero_income.primitives`;
    - a `forbidden` contract stopping `monero_income.cli` from importing `monero_income.primitives` ("no skipping", research R8).
- [X] T003 [P] Create the package skeleton with empty modules: `src/monero_income/__init__.py`, `src/monero_income/py.typed`, `src/monero_income/orchestration/__init__.py`, `src/monero_income/primitives/__init__.py`, plus `tests/__init__.py`, `tests/fakes/__init__.py`, `tests/unit/__init__.py`, `tests/adapters/__init__.py`, `tests/integration/__init__.py`, `tests/cli/__init__.py`
- [X] T004 [P] Append to `.gitignore`: `*.db`, `*.sqlite`, `*.sqlite3`, `config.toml`, `.venv/`, `__pycache__/`, `.coverage`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/` (constitution: real wallet data and database snapshots are never committed)
- [X] T005 Create `tests/conftest.py` with an autouse fixture that uses `monkeypatch.setenv("HOME", str(tmp_path))`. The default config path and default `db_path` expand `~` when `run()` is called (contracts/run-api.md), so every test that omits `config_path` or `db_path` resolves under `tmp_path`, never the real `~/.config/monero-income/config.toml` or `~/.local/share/monero-income/xmr.db`.
- [X] T006 Run `uv sync`, then `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run lint-imports` on the skeleton and fix configuration until they pass (pytest runs from Phase 2 on)

**Checkpoint**: Toolchain installed; static gates pass on an empty package

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Models, storage, wallet adapter, config and settings, and the test double. Every
user story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Models and errors

- [X] T007 [P] Create `src/monero_income/primitives/errors.py` holding every primitive error, so no module imports errors from a sibling it depends on:
  - `StorageError(Exception)` with subclasses `StorageReadError` (the file can't be opened or read), `StorageWriteError` (an insert failed), and `SchemaTooNewError(found: int)`;
  - `WalletError(Exception)` with subclasses `WalletUnreachableError`, `WalletLoginError`, `WalletResponseError`, and `WalletRpcError(code: int, message: str)`;
  - `ConfigFileError(Exception)`.
- [X] T008 [P] Create frozen dataclasses in `src/monero_income/primitives/models.py`:
  - `IncomingEntry(txid: str, height: int, amount_piconero: int, timestamp: int)`
  - `TransactionRecord(txid: str, height: int, amount_piconero: int, occurred_at: int)` (`occurred_at` is UTC Unix seconds)
- [X] T009 [P] Create `RunError(Exception)` in `src/monero_income/orchestration/errors.py`. Docstring: "User-facing failure. str(error) is the complete message, with no 'Error:' prefix." (contracts/run-api.md)

### Schema and storage

- [X] T010 [P] Write `tests/unit/test_migrations.py` against `sqlite3.connect(":memory:", autocommit=False)`. Verify that:
  - migrating from `user_version` 0 creates table `transactions` and index `transactions_height_idx`, and sets `PRAGMA user_version` to 1;
  - `CHECK (length(txid) = 64)`, `CHECK (height > 0)` and `CHECK (amount_piconero > 0)` reject bad rows;
  - `occurred_date` equals `date(occurred_at, 'unixepoch')` (e.g. `occurred_at=1704067199` → `2023-12-31`, `1704067200` → `2024-01-01`);
  - migrating at version 1 is a no-op;
  - `user_version` 2 raises the newer-schema error.
- [X] T011 Implement `src/monero_income/primitives/migrations.py`:
  - `SCHEMA_VERSION = 1`, and a step list where step 1 creates `transactions` exactly as in data-model.md:
    - `txid TEXT PRIMARY KEY CHECK (length(txid) = 64)`
    - `height INTEGER NOT NULL CHECK (height > 0)`
    - `amount_piconero INTEGER NOT NULL CHECK (amount_piconero > 0)`
    - `occurred_at INTEGER NOT NULL`
    - `occurred_date TEXT GENERATED ALWAYS AS (date(occurred_at, 'unixepoch')) STORED`
  - Step 1 also runs `CREATE INDEX transactions_height_idx ON transactions(height)`.
  - `migrate(conn)` reads `PRAGMA user_version`, applies the missing steps and the new `user_version` in one transaction, and commits.
  - A version above `SCHEMA_VERSION` raises `SchemaTooNewError(found)` from `errors.py`.
- [X] T012 [P] Write `tests/unit/test_database.py` (in-memory, migrated). Cover:
  - `last_recorded_height` returns `None` on an empty table, else the max height;
  - `recorded_txids` returns only the requested txids that exist;
  - `insert_records` inserts and commits one batch;
  - a duplicate txid in a batch raises `StorageWriteError` and leaves no row from that batch;
  - an amount above 9,223,372,036,854,775,807 raises `StorageWriteError` (research R6);
  - existing rows are never updated.
- [X] T013 [P] Write `tests/adapters/test_database_files.py` using `tmp_path`:
  - a missing file in a missing directory: `open_database` creates the parent directory and the file, and migrates to version 1;
  - an existing valid database is reopened with its rows intact;
  - an existing file containing `junk` raises `StorageReadError`, and the bytes on disk are unchanged afterwards;
  - a file with `user_version` 2 raises `SchemaTooNewError`.
- [X] T014 Implement `src/monero_income/primitives/database.py`, raising errors from `errors.py`:
  - `open_database(path: Path, timeout: float = 5.0) -> sqlite3.Connection` (`timeout` is passed to `sqlite3.connect` as the lock wait):
    - if the file is missing: `mkdir(parents=True, exist_ok=True)` on the parent, then connect via URI `file:{path}?mode=rwc`;
    - otherwise connect via `mode=rw`;
    - always connect with `uri=True, autocommit=False`;
    - read `PRAGMA user_version`; `sqlite3.DatabaseError` → `StorageReadError`; never delete, rename or recreate an existing file;
    - then call `migrate`.
  - `last_recorded_height(conn) -> int | None` (`SELECT max(height)`).
  - `recorded_txids(conn, txids: Sequence[str]) -> set[str]`.
  - `insert_records(conn, records: Sequence[TransactionRecord]) -> None`: plain `INSERT` (never `OR REPLACE`/`OR IGNORE`), then `commit()`. On any `sqlite3.Error` or `OverflowError`, `rollback()` and raise `StorageWriteError`.

### Wallet RPC adapter

- [X] T015 [P] Write `tests/unit/test_wallet_entries.py` for `parse_incoming(raw: object) -> list[IncomingEntry]`:
  - valid entries map `txid`/`height`/`amount`/`timestamp`;
  - `None` (absent `in`) → `[]`;
  - these raise `WalletResponseError`: a missing field, a JSON float such as `1.0` where an int is expected, `bool` values, negative numbers, a height of 0, and a txid that isn't 64 hex characters;
  - an uppercase hex txid is normalized to lowercase.
- [X] T016 [P] Implement `parse_incoming` in `src/monero_income/primitives/wallet_entries.py` as a pure function. It rejects exactly the cases in data-model.md: "a missing field, a wrong JSON type (including a JSON float where an integer is expected), a negative number, a height of 0, or a txid that isn't 64 hex characters". `WalletResponseError` is imported from `errors.py`.
- [X] T017 [P] Write `tests/adapters/test_wallet_rpc_http.py` using `httpx.MockTransport` (no sockets). Cover:
  - **Requests**: `get_height` posts `{"jsonrpc": "2.0", "id": "0", "method": "get_height", "params": {}}` and returns `result.height`.
  - `get_transfers(lo, hi)` posts exactly these params: `"in": true, "out": false, "pending": false, "failed": false, "pool": false, "filter_by_height": true, "min_height": lo, "max_height": hi`, with no `account_index` or `all_accounts` key (account 0 only, per the spec's Assumptions). The `"out": false` assertion is the test for FR-003 and US1 scenario 2. It returns the raw `in` list, or `None` when absent.
  - **Auth**: with a username, a `401` digest challenge is answered and the retried request succeeds. A final `401` raises `WalletLoginError`.
  - **Other errors**:
    - `httpx.ConnectError` → `WalletUnreachableError`;
    - `httpx.TimeoutException` → `WalletUnreachableError`;
    - HTTP 500 → `WalletResponseError`;
    - a non-JSON body → `WalletResponseError`;
    - a missing `result` → `WalletResponseError`;
    - a JSON-RPC `error` object → `WalletRpcError` with `code` and `message`.
  - **Password**: the configured password never appears in `str()` of any raised error.
  - **Timeout**: the client uses a 20-second timeout.
- [X] T018 Implement `src/monero_income/primitives/wallet_rpc.py`:
  - `WalletRpc(Protocol)` with `get_height() -> int` and `get_transfers(min_height: int, max_height: int) -> TransfersResponse`.
  - `TransfersResponse` (frozen dataclass) holding the raw `incoming: object`.
  - Raises the wallet errors from `errors.py`.
  - `HttpWalletRpc(url: str, username: str | None, password: str | None, timeout: float = 20.0, transport: httpx.BaseTransport | None = None)`:
    - uses an `httpx.Client` with `httpx.DigestAuth(username, password or "")` only when `username` is set, and `httpx.Timeout(timeout)`;
    - sends no account parameters, so the wallet returns account 0 only (contracts/wallet-rpc.md, spec Assumptions);
    - maps errors per contracts/wallet-rpc.md; returns raw JSON only, with no parsing (constitution IV);
    - has no settings-based constructor; the factory `make_wallet` lives in orchestration (T030, contracts/run-api.md).

### Configuration and settings

- [X] T019 [P] Write `tests/adapters/test_config_file.py` using `tmp_path`:
  - a missing file → `None`;
  - valid TOML → its mapping and the file's `st_mode`;
  - invalid TOML → `ConfigFileError` whose message names the path and the parse location but contains no file contents (put a password in the bad file and assert it's absent);
  - an unreadable file (`chmod 000`, skipped when running as root) → `ConfigFileError`.
- [X] T020 [P] Implement `src/monero_income/primitives/config_file.py`:
  - raises `ConfigFileError` from `errors.py`;
  - `RawConfig(values: Mapping[str, object], mode: int)`;
  - `read_config(path: Path) -> RawConfig | None`, using `tomllib`. It only reads the file and its mode, with no validation (constitution IV).
- [X] T021 [P] Write `tests/unit/test_settings.py` for `resolve_settings`. Cover:
  - **Precedence**: option over file over default, for `rpc_url`, `username` and `db_path`.
  - **Defaults**: `rpc_url` `http://127.0.0.1:18088/json_rpc` and `db_path` `~/.local/share/monero-income/xmr.db` (with `~` expanded).
  - **`rpc_url` validation**: the scheme must be `http` or `https`, it must have a host, and it must not contain user info such as `http://u:p@h/json_rpc`.
  - **Username and password**:
    - an empty `username` is invalid;
    - `password` without `username` raises a `RunError` containing `password is set in <config path> but username is not`;
    - `password` is accepted only from the file;
    - a username without a password is allowed.
  - **Keys**: an unknown key returns a warning naming the key; a known key of the wrong type raises `RunError` (`invalid <key>: …`).
  - **Permissions**: `is_readable_by_others(0o100644)` is True and `is_readable_by_others(0o100600)` is False.
  - **Password secrecy**: no error or warning text contains the password value.
- [X] T022 Implement `src/monero_income/orchestration/settings.py`, all pure:
  - `CliOptions(rpc_url: str | None = None, username: str | None = None, db_path: str | None = None)` (frozen).
  - `Settings(rpc_url: str, username: str | None, password: str | None, db_path: Path)` (frozen; `repr` must hide `password`, e.g. `field(repr=False)`).
  - `default_config_path() -> Path`, returning `Path("~/.config/monero-income/config.toml").expanduser()` evaluated at call time (not import time). The default `db_path` is also expanded inside `resolve_settings`, so redirecting `HOME` redirects both.
  - A known-key table (`rpc_url`, `username`, `password`, `db_path`) that later features can extend.
  - `resolve_settings(options: CliOptions, raw: RawConfig | None, config_path: Path) -> tuple[Settings, list[str]]`, returning the settings and any warnings and raising `RunError` with the contracts/cli.md wording.
  - `is_readable_by_others(mode: int) -> bool` (`mode & 0o004`). `resolve_settings` adds the warning `config file <path> is readable by other users; run chmod 600 on it` when it applies.

### Test double

- [X] T023 [P] Implement `FakeWalletRpc` in `tests/fakes/wallet.py`:
  - holds a list of raw `in` entry dicts and a `height`;
  - `get_transfers(min_height, max_height)` returns the entries with `min_height < height <= max_height` (exclusive min, as in research R5) and logs each call's bounds;
  - `fail_on_call: int | None` and `failure: BaseException` raise on the Nth `get_transfers` call, which can also be `KeyboardInterrupt`;
  - a helper `entry(txid_seed, height, amount, timestamp, subaddr_minor=0)` builds a valid raw entry with a 64-hex txid.

  It must satisfy the `WalletRpc` Protocol under mypy.

**Checkpoint**: `uv run pytest` passes for the Phase 2 tests; all static gates pass

---

## Phase 3: User Story 1 - Record incoming transactions from the wallet (Priority: P1) 🎯 MVP

**Goal**: A first run creates the database and records every confirmed incoming transaction
(txid, height, exact piconero amount, UTC timestamp), combining entries per txid. Covers
FR-001, FR-002, FR-004 to FR-008, FR-012, FR-016, FR-017.

**Independent Test**: Run `run()` with a `FakeWalletRpc` holding entries spread over several
10,000-block windows (including a txid paid to two subaddresses) and an empty database. Every
txid is stored once with exact fields, and `SyncResult.recorded` equals the number of distinct
txids.

### Tests for User Story 1 ⚠️ (write first, confirm they fail)

- [X] T024 [P] [US1] Write the window and combine tests in `tests/unit/test_transform.py`:
  - **Windows**:
    - `fetch_windows(0, 25000) == [(0, 10000), (10000, 20000), (20000, 25000)]`;
    - `fetch_windows(0, 0) == []`;
    - `fetch_windows(5, 10005) == [(5, 10005)]`;
    - windows are ascending, gap-free and non-overlapping.
  - **Combine**:
    - `combine_by_txid` sums amounts for a repeated txid (e.g. `400000000000 + 123456789012`) and keeps height/timestamp;
    - it returns one `TransactionRecord` per txid in ascending height order.
- [X] T025 [P] [US1] Write `tests/integration/test_first_sync.py`. It calls `run()` with `config_path=tmp_path/"absent.toml"`, a `wallet_factory` returning a `FakeWalletRpc`, and `db_path` set to a `tmp_path` file through the real `open_database`, so the rows can be inspected after `run()` closes its connection. Fake height 25000; entries at heights 5, 10000, 10001 and 24999, one txid split over two subaddresses. Assert:
  - all distinct txids are stored with exact `height`, `amount_piconero` and `occurred_at`, including `123456789012` stored exactly (US1-4);
  - `occurred_date` is the UTC date;
  - `SyncResult.recorded` is correct;
  - the fake saw windows `(0,10000]`, `(10000,20000]`, `(20000,25000]`.

  FR-003 and US1 scenario 2 (only incoming recorded) are covered by T017's `"out": false` assertion; the fake holds only incoming entries.
- [X] T026 [P] [US1] Write `tests/integration/test_persistence.py` using `tmp_path` and the real `open_database`. After a first `run()`, a second `open_database` on the same path sees identical rows (US1-3, FR-016). A `db_path` in a missing directory is created.
- [X] T027 [P] [US1] Write `tests/cli/test_cli_success.py` with `typer.testing.CliRunner`, monkeypatching `monero_income.cli.run` to capture `CliOptions` and return a `SyncResult`. Assert:
  - the stdout line is exactly `Recorded 1 new transaction.` for 1 and `Recorded 3 new transactions.` for 3, with exit 0;
  - `--rpc-url`, `--username` and `--db-path` map onto `CliOptions`;
  - `--help` shows no `--password` option and no subcommands (FR-001, FR-018).

### Implementation for User Story 1

- [X] T028 [US1] Implement in `src/monero_income/orchestration/transform.py`:
  - `WINDOW_SIZE = 10_000`;
  - `fetch_windows(start_after: int, wallet_height: int) -> list[tuple[int, int]]`: ascending consecutive `(lo, hi]` windows covering `start_after < h <= wallet_height`;
  - `combine_by_txid(entries: Sequence[IncomingEntry]) -> list[TransactionRecord]`.

  All pure (makes T024 pass).
- [X] T029 [US1] Implement `sync(conn: sqlite3.Connection, wallet: WalletRpc) -> int` in `src/monero_income/orchestration/sync.py`:
  - `start_after = 0` (first run; US2 replaces this with the resume position);
  - `height = wallet.get_height()`;
  - for each window from `fetch_windows`, in order: `get_transfers(lo, hi)` → `parse_incoming` → `combine_by_txid` → `insert_records` (commits that window);
  - return the total inserted.
- [X] T030 [US1] Implement `run()` in `src/monero_income/orchestration/run.py` with the exact signature from contracts/run-api.md. It:
  - uses `config_path or default_config_path()`, calls `read_config` on it, then `resolve_settings`, sending each warning to `reporter.warning` immediately;
  - opens `conn = connect(settings.db_path)`;
  - builds `wallet = wallet_factory(settings)`;
  - computes `recorded = sync(conn, wallet)` and closes `conn` in `finally`;
  - returns `SyncResult(recorded)`.

  Also define `Reporter(Protocol)` with `warning(message: str) -> None`, `SyncResult(recorded: int)` (frozen), and the default factory `make_wallet(settings) -> WalletRpc`, which returns `HttpWalletRpc(settings.rpc_url, settings.username, settings.password)`.
- [X] T031 [US1] Export `run`, `CliOptions`, `Reporter`, `SyncResult` and `RunError` from `src/monero_income/orchestration/__init__.py`. Nothing else is public.
- [X] T032 [US1] Implement `src/monero_income/cli.py`:
  - a Typer app with `pretty_exceptions_enable=False` and a single command (no subcommands) taking options `--rpc-url`, `--username` and `--db-path` (no `--password`);
  - it builds `CliOptions`, passes a stderr reporter that prints `Warning: <message>`, and calls `run()`;
  - it prints `Recorded 1 new transaction.` or `Recorded N new transactions.` to stdout;
  - `main()` is the console-script entry point.

  Import only from `monero_income.orchestration` (makes T025–T027 pass).

**Checkpoint**: The MVP works. A first run against a wallet records everything; gates pass.

---

## Phase 4: User Story 2 - Re-sync safely and incrementally (Priority: P2)

**Goal**: Later runs resume from the last recorded height minus a 60-block overlap. They add
only new txids, never touch existing rows, and say "No new transactions found." when nothing
is new. Covers FR-008 to FR-011 and SC-003 and SC-006.

**Independent Test**: Run `run()` twice against the same fake and a `tmp_path` database file. The
second run returns `recorded == 0` and the table dump is byte-for-byte identical. Add one
entry above the last height; a third run adds only it.

### Tests for User Story 2 ⚠️ (write first, confirm they fail)

- [X] T033 [P] [US2] Add these tests to `tests/unit/test_transform.py`:
  - `first_window_start(None) == 0`, `first_window_start(30) == 0` and `first_window_start(1000) == 939` (`max(last - 61, 0)`: the 60-block overlap is inclusive and `min_height` is exclusive, research R5);
  - `select_new` drops records whose txid is in the recorded set and keeps order.
- [X] T034 [P] [US2] Write `tests/integration/test_resync.py`, using a `tmp_path` database file shared by every `run()` call in a test. Assert:
  - **No changes (US2-1)**: a second run returns `recorded == 0`, and `SELECT * FROM transactions ORDER BY txid` is identical before and after.
  - **New entry (US2-2)**: an entry added above the last height is the only addition.
  - **Overlap**: an entry already recorded at height H, reported again by the fake at H-30 (a reorg), is not duplicated, and its stored row is unchanged.
  - **Resume position**: the fake's first logged window on the second run starts at `last_height - 61`.
  - **Empty wallet**: `recorded == 0`.
- [X] T035 [P] [US2] Add to `tests/cli/test_cli_success.py`: `SyncResult(0)` prints exactly `No new transactions found.` and exits 0 (FR-011).
- [X] T036 [P] [US2] Write `tests/integration/test_performance.py` (SC-006). With 10,000 rows pre-inserted into a `tmp_path` database file (via `open_database` and `insert_records`, then closed) and a fake that reports nothing new, `run()` completes in under 5 seconds (`time.perf_counter`), not counting fake time.

### Implementation for User Story 2

- [X] T037 [US2] Add `OVERLAP_BLOCKS = 60`, `first_window_start(last_height: int | None) -> int` and `select_new(records, recorded_txids: set[str]) -> list[TransactionRecord]` to `src/monero_income/orchestration/transform.py` (pure).
- [X] T038 [US2] Update `sync()` in `src/monero_income/orchestration/sync.py` to:
  - use `start_after = first_window_start(last_recorded_height(conn))`;
  - per window, filter with `select_new(records, recorded_txids(conn, [r.txid for r in records]))` before `insert_records`;
  - skip the insert when nothing is new.
- [X] T039 [US2] Update `src/monero_income/cli.py` to print `No new transactions found.` when `recorded == 0` (makes T033–T036 pass).

**Checkpoint**: US1 and US2 both pass; repeated runs are idempotent

---

## Phase 5: User Story 3 - Recover from interruptions and errors (Priority: P3)

**Goal**: An interruption keeps every committed window and rolls back the one in progress;
the next run completes the records. Every failure is a one-line `Error: …` message with the
right exit code, never a traceback and never the password. Covers FR-013 to FR-015, FR-018,
FR-019 and SC-004 and SC-005.

**Independent Test**: Make the fake fail on its third `get_transfers` call. `run()` raises
`RunError`, the windows 1–2 rows are present, and a following successful run leaves a table
identical to a single uninterrupted run on a fresh database.

### Tests for User Story 3 ⚠️ (write first, confirm they fail)

- [X] T040 [P] [US3] Write `tests/integration/test_interruption.py`, using `tmp_path` database files:
  - **Wallet failure (US3-1, SC-004)**: `fail_on_call=3` with `WalletUnreachableError` raises `RunError`, and only windows 1–2 are stored. The next run's table equals a fresh uninterrupted run's table.
  - **Ctrl-C**: `fail_on_call=2` with `KeyboardInterrupt` propagates `KeyboardInterrupt`. Reopening the file with `open_database` succeeds (no lock is left behind) and shows window 1's rows and nothing from window 2.
  - **Partial window (FR-013)**: the third window holds one normal entry and one at 9,223,372,036,854,775,808 piconero, which overflows on insert. `run()` raises `RunError`; neither of that window's rows is stored, and windows 1–2 stay.
- [X] T041 [P] [US3] Write `tests/integration/test_concurrent_run.py` (spec edge case "Second run started while one is in progress"). On a `tmp_path` database with recorded rows, a second connection runs `BEGIN IMMEDIATE` and holds the write lock while `run()` is called with `connect=lambda p: open_database(p, timeout=0.1)` and a fake that reports one new entry. Assert:
  - `run()` raises `RunError` containing `cannot write to database` (or `cannot read database` if the lock hits at open);
  - after the holder rolls back, the previously recorded rows are intact and unchanged.
- [X] T042 [P] [US3] Write `tests/integration/test_errors.py`. Each case raises `RunError` whose message contains the contracts/cli.md category phrase:
  - `cannot reach the wallet at` (unreachable);
  - `rejected the login` (login);
  - `the wallet returned an error` (`WalletRpcError`);
  - `unexpected response from the wallet` (`WalletResponseError`);
  - `cannot read database` (a `tmp_path` junk file, whose bytes are unchanged afterwards);
  - `cannot write to database` (the fake reports an amount of 9,223,372,036,854,775,808 piconero, which overflows on insert);
  - `newer version of monero-income` (`user_version` 2);
  - `cannot read config file` (invalid TOML);
  - `password is set` (password without username; assert `wallet_factory` is never called);
  - `invalid rpc_url`.

  Across all cases, assert that the distinctive password `pw-Zq9!secret` never appears in any message and that no message contains `transfer` (case-insensitive).
- [X] T043 [P] [US3] Write `tests/cli/test_cli_errors.py` with `CliRunner`, monkeypatching `run`:
  - `RunError("x")` → stderr `Error: x`, exit 1;
  - `KeyboardInterrupt` → `Error: interrupted; anything already recorded was kept`, exit 130;
  - `ValueError("boom")` → `Error: unexpected ValueError: boom`, exit 1;
  - an unknown option → exit 2;
  - a warning sent through the reporter → stderr `Warning: …` while the run continues;
  - in every case, the output contains no `Traceback`.

### Implementation for User Story 3

- [X] T044 [US3] Update `sync()` in `src/monero_income/orchestration/sync.py`: wrap each window in `try/except BaseException: conn.rollback(); raise`, so an interruption or error mid-window leaves no open transaction and no partial window. Windows already committed stay.
- [X] T045 [US3] Update `run()` in `src/monero_income/orchestration/run.py` to translate primitive errors into `RunError`, using the contracts/cli.md wording:
  - `ConfigFileError` → `cannot read config file <path>: <reason>`;
  - `SchemaTooNewError` → `database <path> was written by a newer version of monero-income (schema N)`;
  - `StorageReadError` → `cannot read database <path>: <reason>. The file was not changed.`;
  - `StorageWriteError` → `cannot write to database <path>: <reason>. Transactions recorded before this error were kept.`;
  - `WalletUnreachableError` → `cannot reach the wallet at <rpc_url>: <reason>`;
  - `WalletLoginError` → `the wallet at <rpc_url> rejected the login; check username and password`;
  - `WalletRpcError` → `the wallet returned an error: <message>`;
  - `WalletResponseError` → `unexpected response from the wallet: <reason>`.

  Let `KeyboardInterrupt` propagate. Make sure no message includes the password or "transfer".
- [X] T046 [US3] Update `src/monero_income/cli.py` to wrap the `run()` call:
  - `RunError` → `Error: <message>` on stderr, `raise typer.Exit(1)`;
  - `KeyboardInterrupt` → `Error: interrupted; anything already recorded was kept`, exit 130;
  - any other `Exception` → `Error: unexpected <TypeName>: <message>`, exit 1.

  This makes T040–T043 pass.

**Checkpoint**: All three stories pass independently; every failure path is a clean message

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Gates, wording sweep, docs, and end-to-end validation

- [ ] T047 [P] Add a test in `tests/cli/test_messages.py` that collects every string literal in `src/monero_income/cli.py` and `src/monero_income/orchestration/` (via `ast`) and asserts none contains `transfer` (case-insensitive) (FR-019). No exemptions: `get_transfers` lives only in primitives, which isn't scanned.
- [ ] T048 [P] Add a usage section to `README.md`: install with `uv`, the config file keys from contracts/config.md (including `chmod 600`), the command `monero-income` and its options, and the output lines. Update the Status section to say feature 001 (sync) is available.
- [ ] T049 Run all gates and fix any failures until all five pass with coverage ≥ 90%: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run lint-imports`, `uv run pytest`.
- [ ] T050 Run the manual end-to-end checks in `specs/001-sync-incoming-transactions/quickstart.md` §3 against a stagenet `monero-wallet-rpc`, and record the results in the PR description. Don't commit any database or wallet files.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none. T001 → T002 (same file); T003 and T004 in parallel; T005 after T003 creates `tests/`; T006 last.
- **Foundational (Phase 2)**: depends on Setup and blocks all stories.
  - T007 (`errors.py`) comes first: T011, T014, T016, T018 and T020 import from it.
  - T010 → T011, and T012/T013 → T014 (T014 also needs T011).
  - T015 → T016, and T017 → T018.
  - T019 → T020, and T021 → T022 (T022 also needs T009 and T020).
  - T023 needs T018's Protocol.
- **US1 (Phase 3)**: depends on Phase 2. T024–T027 [P] → T028 → T029 → T030 → T031 → T032.
- **US2 (Phase 4)**: depends on US1. It changes US1's `sync()` and `cli.py`; its tests can be written in parallel with US1 work. T033–T036 [P] → T037 → T038 → T039.
- **US3 (Phase 5)**: depends on US1. It changes `sync()`, `run()` and `cli.py`, and is independent of US2's behavior. T040–T043 [P] → T044 → T045 → T046.
- **Polish (Phase 6)**: depends on all stories.

### User Story Dependencies

- **US1 (P1)**: only needs Foundational. It's the MVP.
- **US2 (P2)**: builds on US1's `sync()`; testable alone with its own scenarios.
- **US3 (P3)**: builds on US1's `sync()`/`run()`/`cli.py`; testable alone. If US2 and US3 run in parallel, coordinate edits to `sync.py` and `cli.py`.

### Within Each User Story

- Tests are written first and fail, then the implementation makes them pass.
- Pure transforms → `sync()` → `run()` → CLI.

---

## Parallel Examples

### Phase 2 (Foundational)

```bash
Task: "T007 errors in src/monero_income/primitives/errors.py"
Task: "T008 models in src/monero_income/primitives/models.py"
Task: "T009 RunError in src/monero_income/orchestration/errors.py"
Task: "T010 tests/unit/test_migrations.py"
Task: "T015 tests/unit/test_wallet_entries.py"
Task: "T017 tests/adapters/test_wallet_rpc_http.py"
Task: "T019 tests/adapters/test_config_file.py"
Task: "T021 tests/unit/test_settings.py"
```

### User Story 1

```bash
Task: "T024 window/combine tests in tests/unit/test_transform.py"
Task: "T025 tests/integration/test_first_sync.py"
Task: "T026 tests/integration/test_persistence.py"
Task: "T027 tests/cli/test_cli_success.py"
```

### User Story 2

```bash
Task: "T034 tests/integration/test_resync.py"
Task: "T036 tests/integration/test_performance.py"
```

### User Story 3

```bash
Task: "T040 tests/integration/test_interruption.py"
Task: "T041 tests/integration/test_concurrent_run.py"
Task: "T042 tests/integration/test_errors.py"
Task: "T043 tests/cli/test_cli_errors.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup → Phase 2 Foundational (all gates green).
2. Phase 3 (US1): a first run records the wallet's incoming transactions.
3. **Stop and validate**: run the T025/T026 scenarios, plus quickstart §3 "First run" against a stagenet wallet.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → first sync works (MVP).
3. US2 → repeat runs are incremental and idempotent.
4. US3 → interruptions and every error path are clean.
5. Polish → wording sweep, README, all gates, manual quickstart.

---

## Notes

- **Commits**: commit after each task or logical group, and never commit `.db` or `config.toml` files.
