---

description: "Task list for feature 002: USD valuation of recorded transactions"
---

# Tasks: USD Valuation of Recorded Transactions

**Input**: Design documents from `specs/002-usd-valuation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (cli.md, config.md,
price-source.md, import-csv.md, run-api.md), quickstart.md

**Tests**: Included. Constitution v1.2.0 requires them: VII sets a 90% coverage floor, and V
requires the price source to be faked behind a Protocol. Write each story's tests first and
confirm they fail.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 from spec.md
- Paths are relative to the repository root. Feature 001's layout and conventions apply.

## Rules that apply to every task

- Prices and USD values are `Decimal` and amounts are `int` piconero; never `float`
  (constitution III). JSON is decoded with `json.loads(content, parse_float=Decimal)`, never
  `response.json()` (research R4).
- Functions that fetch or persist don't reshape; parsing, cutoff, settling, ordering, and
  import validation are pure functions (constitution IV).
- Tests never touch the network or real time: use `FakePriceSource`, `FakeClock`, and
  `RecordingSleep` (T014). The autouse fixture from T023 replaces the default price source
  and sleep in every test (constitution V).
- The API key never appears in any output, error, warning, or `repr` (FR-015, SC-008).
  User-facing text never says "transfer(s)" (FR-018).
- A final price is never updated or deleted (FR-006, constitution VI).

---

## Phase 1: Setup

**Purpose**: Confirm the starting point

- [X] T001 On branch `002-usd-valuation`, run `uv sync` and the five gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run lint-imports`, `uv run pytest`), and confirm they pass before any change. No new dependencies are needed (plan.md).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Errors, models, schema v2, price storage, settings, pure valuation rules, and
test doubles. Every story depends on these.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Errors and models

- [X] T002 [P] Add to `src/monero_income/primitives/errors.py`:
  - `PriceSourceError(Exception)` with subclasses:
    - `PriceRateLimitedError(retry_after: float | None)`
    - `PriceKeyRejectedError`
    - `PriceUnavailableError(reason: str)`
  - `ImportFileError(line: int | None, reason: str)`, whose message is `line <n>: <reason>`, or just `<reason>` when `line` is `None`.

  No message may include an API key (contracts/price-source.md).
- [X] T003 [P] Add frozen dataclasses to `src/monero_income/primitives/models.py`:
  - `DailyPrice(date_utc: date, usd_price: Decimal, status: Literal["provisional", "final"], source: Literal["api", "import"], fetched_at: int)`
  - `PriceNeed(date_utc: date, has_provisional: bool)`
  - `ImportRow(line: int, date_utc: date, usd_price: Decimal)`

### Schema v2 and price storage

- [X] T004 [P] Add to `tests/unit/test_migrations.py`:
  - **Migrating from version 1:** build a version-1 database with step 1's SQL and transaction rows, then call `migrate`. Expect `user_version` 2, the rows intact, and `daily_prices` present and empty.
  - **Migrating from 0:** expect version 2.
  - **Table checks:** `daily_prices` rejects `date_utc` values that don't match `GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'`, and rejects `status` outside `('provisional', 'final')` and `source` outside `('api', 'import')`.
  - **Triggers:** updating a row whose `status = 'final'` raises `sqlite3.IntegrityError` ("final price is immutable"); updating a provisional row succeeds; deleting any row raises.
  - **Newer schema:** version 3 is refused.
- [X] T005 Add migration step 2 to `_STEPS` in `src/monero_income/primitives/migrations.py`, exactly as in data-model.md, so `SCHEMA_VERSION` becomes 2:
  - `CREATE TABLE daily_prices` with these columns:
    - `date_utc TEXT PRIMARY KEY CHECK (date_utc GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')`
    - `usd_price TEXT NOT NULL`
    - `status TEXT NOT NULL CHECK (status IN ('provisional', 'final'))`
    - `source TEXT NOT NULL CHECK (source IN ('api', 'import'))`
    - `fetched_at INTEGER NOT NULL`
  - Trigger `daily_prices_final_no_update` (`BEFORE UPDATE ON daily_prices WHEN OLD.status = 'final'`, which runs `SELECT RAISE(ABORT, 'final price is immutable')`).
  - Trigger `daily_prices_no_delete` (`BEFORE DELETE ON daily_prices`, which runs `SELECT RAISE(ABORT, 'prices are never deleted')`).
- [X] T006 Update feature 001's schema-version expectations for version 2:
  - in `tests/unit/test_migrations.py`, `SCHEMA_VERSION == 2` and `user_version == 2`; the newer-schema test uses 3;
  - in `tests/adapters/test_database_files.py`, a new database migrates to version 2 and the newer-schema case uses `user_version` 3;
  - in `tests/integration/test_errors.py`, `test_newer_schema` sets `user_version` 3.
- [X] T007 [P] Write `tests/unit/test_prices_db.py` (in-memory, migrated). Cover:
  - `price_needs` returns one `PriceNeed` per distinct `transactions.occurred_date` with no price or a provisional one (`has_provisional` set accordingly), ascending, and omits final days;
  - `upsert_price` inserts, replaces a provisional row, leaves a final row unchanged (the conditional upsert does nothing), and commits;
  - `priced_days` returns the requested dates that have any price;
  - `insert_imported` inserts all rows in one transaction and rolls back all of them if any conflicts (`StorageWriteError`);
  - `all_days_final` is True only when at least one transaction is recorded and every transaction day has a final price (False for an empty database);
  - prices round-trip exactly, e.g. `Decimal("152.3456")` and `Decimal("0.000000012345678901234567890123")`, with no exponent in the stored text.
- [X] T008 Implement `src/monero_income/primitives/prices_db.py`. I/O only; errors are `StorageWriteError` from `errors.py`.
  - `price_needs(conn) -> list[PriceNeed]`.
  - `upsert_price(conn, price: DailyPrice) -> None`: `INSERT … ON CONFLICT(date_utc) DO UPDATE SET usd_price=excluded.usd_price, status=excluded.status, source=excluded.source, fetched_at=excluded.fetched_at WHERE daily_prices.status = 'provisional'`, then commit; roll back on error.
  - `priced_days(conn, days: Sequence[date]) -> set[date]`.
  - `insert_imported(conn, prices: Sequence[DailyPrice]) -> None`: plain `INSERT`, one transaction.
  - `all_days_final(conn) -> bool`.
  - Prices are stored with `format(price, "f")`.

### Settings

- [X] T009 [P] Add tests to `tests/unit/test_settings.py` for the new keys (contracts/config.md). Cover:
  - **Defaults:**
    - `coingecko_url` is `https://api.coingecko.com/api/v3`, or `https://pro-api.coingecko.com/api/v3` when the key type is `pro`;
    - an explicit URL wins;
    - `coin_id` is `monero`;
    - `min_request_delay` is `None`.
  - **The key and its type:**
    - can come from the file or from `CliOptions(coingecko_api_key=…, coingecko_api_key_type=…)`, and the command line overrides the file;
    - a key without a type raises `RunError` containing `invalid coingecko_api_key_type: required when coingecko_api_key is set`;
    - a type other than `demo`/`pro` is invalid;
    - a type without a key gives a warning.
  - **Other validation:**
    - `coingecko_url` follows the `rpc_url` rules (http/https, a host, no user info);
    - `coin_id` must match `[a-z0-9-]+`;
    - `min_request_delay` accepts a TOML int or float, `0 ≤ value ≤ 60`, and is converted with `Decimal(str(value))`; a string or a negative value is invalid;
    - `CliOptions.import_prices` is passed through.
  - **Key secrecy:** the key never appears in `repr(settings)`, in warnings, or in any `RunError`.
- [X] T010 Extend `src/monero_income/orchestration/settings.py`:
  - add `coingecko_url`, `coin_id`, `coingecko_api_key`, `coingecko_api_key_type`, and `min_request_delay` to `KNOWN_KEYS`;
  - give `CliOptions` the fields `import_prices`, `coingecko_api_key`, and `coingecko_api_key_type` (all `str | None = None`);
  - give `Settings` the fields `coingecko_url: str`, `coin_id: str`, `api_key: str | None` (`field(repr=False)`), `api_key_type: Literal["demo", "pro"] | None`, `min_request_delay: Decimal | None`, and `import_prices: Path | None`, with defaults so feature 001's settings tests still construct `Settings`;
  - add a numeric reader for `min_request_delay` next to `_file_string`, and reuse the URL check for `coingecko_url`.

  This makes T009 pass.

### Pure valuation rules

- [X] T011 [P] Write `tests/unit/test_valuation.py`. Cover:
  - `history_cutoff(date(2026, 10, 17)) == date(2025, 10, 18)` (364 days);
  - `plan_lookups(needs, today)` splits into `requestable`, ascending (FR-024), and `too_old`, which includes provisional days older than the cutoff;
  - `settled_at(date(2026, 10, 16)) == datetime(2026, 10, 17, 1, 0, tzinfo=UTC)`;
  - `price_status(day, now)` is `"provisional"` at `settled_at - 1 s` and `"final"` at `settled_at`;
  - `default_delay(True) == Decimal("2.5")` and `default_delay(False) == Decimal("6.0")`;
  - `usd_value(1_234_567_890_123, Decimal("152.3456")) == Decimal("188.0809859615225088")` exactly;
  - `usd_value` stays exact with a 20-digit amount and a 30-significant-digit price, where the default 28-digit context would round (research R4).

  Then implement them all, pure, in `src/monero_income/orchestration/valuation.py`. `usd_value` computes `Decimal(amount) * price` under `localcontext(prec=<digits of both operands + 2>, traps=[Inexact])`, then applies `.scaleb(-12)`.

### Price answers (shared by the client, pricing, and the fakes)

- [X] T012 [P] Write `tests/unit/test_price_parse.py` for `parse_history_price(body)` and the answer types `Price(usd_price: Decimal)`, `NoPrice(reason: str)`, and `OutsideHistory()`:
  - `{"market_data": {"current_price": {"usd": Decimal("152.3456")}}}` → `Price(Decimal("152.3456"))`;
  - an `int` `152` → `Price(Decimal(152))`;
  - missing `market_data`, `current_price`, or `usd` → `NoPrice`;
  - `True`, `0`, negative values, a string, `Decimal("NaN")`, and `Decimal("Infinity")` → `NoPrice("invalid price")` (FR-016).
- [X] T013 Implement `src/monero_income/primitives/price_parse.py`, pure: the `Price`, `NoPrice`, and `OutsideHistory` frozen dataclasses, the type alias `PriceAnswer = Price | NoPrice | OutsideHistory`, and `parse_history_price(body: object) -> Price | NoPrice` per contracts/price-source.md step 5. This makes T012 pass.

### Test doubles

- [X] T014 Create the test doubles:
  - `tests/fakes/price_source.py`: `FakePriceSource`, holding a map `date → PriceAnswer | BaseException`. An exception is raised once, then removed unless `repeat=True`. It records requested dates in `requests`, and returns `NoPrice("no price for this date")` for unmapped days.
  - `tests/fakes/clock.py`: `FakeClock`, holding a settable aware-UTC `now` that is callable as `clock()`, and `RecordingSleep`, whose `__call__(seconds)` appends to `calls` and advances an optional linked `FakeClock`.

  Add a mypy protocol check like `tests/fakes/wallet.py` has. Uses the answer types from T013.

**Checkpoint**: The Phase 2 tests pass, all feature 001 tests pass on schema v2, and all gates are green.

---

## Phase 3: User Story 1 - Value recorded transactions in USD (Priority: P1) 🎯 MVP

**Goal**: After a successful sync, each day with transactions and no final price is looked up
oldest first, recorded with the right status (provisional or final), and valued exactly.
Covers FR-001 to FR-008, FR-013 to FR-015, FR-017, FR-018, FR-021, FR-022, and FR-024, and
SC-001 to SC-003, SC-008, and SC-009.

**Independent Test**: Three transaction days and a `FakePriceSource` answering all three: three
prices are recorded, each `usd_value` is the exact product, and a second run makes no request
for final days.

### Tests for User Story 1 ⚠️ (write first, confirm they fail)

- [X] T015 [P] [US1] Write `tests/adapters/test_price_source_http.py` with `httpx.MockTransport` for `CoinGeckoPriceSource`. Cover:
  - **Requests:**
    - `GET {url}/coins/monero/history?date=16-10-2026&localization=false` for `date(2026, 10, 16)`;
    - the header `x-cg-demo-api-key` for type `demo`, `x-cg-pro-api-key` for `pro`, and no key header without a key;
    - `accept: application/json`;
    - a 20 s timeout (`request.extensions["timeout"]`).
  - **200 responses:** `"usd": 152.3456` in the JSON text returns exactly `Decimal("152.3456")`, so it's decoded with `parse_float`.
  - **401 with error_code 10012:** the body `{"error":{"status":{"error_code":10012,"error_message":"…"}}}` → `OutsideHistory()`; the alternate `status.error_code` and top-level `error_code` shapes are also recognized.
  - **Other failures:**
    - any other 401 (including an empty body) → `PriceKeyRejectedError`;
    - 429 → `PriceRateLimitedError`, with `retry_after` parsed from a `Retry-After: 30` header, or `None`;
    - HTTP 500, a non-JSON body, `httpx.ConnectError`, and `httpx.ReadTimeout` → `PriceUnavailableError`.
  - **Key secrecy:** a distinctive key never appears in `str()` of any raised error.
- [X] T016 [P] [US1] Write `tests/integration/test_pricing.py`, calling `run()` with a `tmp_path` database, the fake wallet, `FakePriceSource`, `FakeClock`, and `RecordingSleep`. Cover:
  - **US1-1/2/3:** three transaction days are all priced; two transactions on one day share its price; `usd_value` for a 1.234567890123 XMR transaction at `152.3456` is `188.0809859615225088`.
  - **US1-4/6:** with all days final, a second run makes 0 requests, and `RunResult.pricing.all_final` is True.
  - **US1-5:** when the sync fails (the wallet raises), there are 0 price requests and a `RunError`.
  - **US1-7:** today gets `status = 'provisional'`.
  - **US1-8:** with the clock before `settled_at`, a provisional day is requested again, replaced, and still provisional.
  - **US1-9:** with the clock days after `settled_at`, it's requested once and becomes `final`.
  - **SC-009:** advancing the clock without running never changes a status.
  - **FR-024:** requests are in ascending date order.
  - **Summary:** `RunResult.pricing.priced` and `.provisional` counts are correct.
- [X] T017 [P] [US1] Add to `tests/cli/test_cli_success.py`, monkeypatching `run` to return a `RunResult`:
  - the sync line is followed by `Priced 3 days (1 provisional).`, with `Priced 1 day.` for singular and no provisional part;
  - `All transactions are valued.` when `all_final` is True, and not printed for an empty database (`RunResult(recorded=0, …)` with `pricing.all_final` False, as `all_days_final` returns for no transactions);
  - `--coingecko-api-key` and `--coingecko-api-key-type pro` map onto `CliOptions`;
  - a distinctive key passed with `--coingecko-api-key` appears nowhere in stdout or stderr (SC-008).

  Update the existing tests to construct `RunResult` instead of `SyncResult`.

### Implementation for User Story 1

- [X] T018 [US1] Implement `src/monero_income/primitives/price_source.py`:
  - `PriceSource(Protocol)` with `daily_price(day: date) -> PriceAnswer`.
  - `CoinGeckoPriceSource(base_url: str, coin_id: str, api_key: str | None, api_key_type: Literal["demo", "pro"] | None, timeout: float = 20.0, transport: httpx.BaseTransport | None = None)`, with a `close()` method.
  - Each call makes exactly one request and classifies the response per contracts/price-source.md steps 1–4, reading the body before classifying a 401. It does no retrying or pacing.

  This makes T015 pass.
- [X] T019 [US1] Implement `src/monero_income/orchestration/pricing.py`. Add `PricingSummary(priced: int, provisional: int, no_price: int, not_refreshed: int, too_old: int, all_final: bool, stopped: StopReason | None)`, `StopReason(kind: Literal["rate_limited", "key_rejected", "unavailable"], reason: str)`, and `price_days(conn, source, *, today, clock, sleep, delay) -> PricingSummary`:
  - **Plan:** `price_needs` → `plan_lookups`.
  - **Each requestable day, oldest first:**
    - `Price` → `upsert_price(DailyPrice(status=price_status(day, clock()), source="api", fetched_at=int(clock().timestamp())))`;
    - `NoPrice` → count `no_price`, or `not_refreshed` when the day already had a provisional price;
    - `OutsideHistory` → count `too_old`.
  - **Afterwards:** `all_final` comes from `all_days_final(conn)`.

  Pacing, retry, and stop handling are added in US2 (T026); for now, `PriceSourceError` propagates.
- [X] T020 [US1] Update `src/monero_income/orchestration/run.py` to the contracts/run-api.md signature:
  - **Result:** rename `SyncResult` to `RunResult(recorded: int, imported: ImportSummary | None, pricing: PricingSummary)`; define `ImportSummary(imported: int, skipped: int)` in `src/monero_income/orchestration/price_import.py` (create the module with just this dataclass if US4 isn't done yet) and re-export it from `run.py`.
  - **Defaults:** `price_source_factory`, `clock`, and `sleep` default to `None` and are resolved **at call time** to `make_price_source`, `utc_now`, and the module-level `_sleep = time.sleep`, so the T023 fixture can replace them. `make_price_source(settings)` builds `CoinGeckoPriceSource(settings.coingecko_url, settings.coin_id, settings.api_key, settings.api_key_type)`.
  - **Order:** after a successful sync, call `price_days` with `today = clock().date()` and `delay = settings.min_request_delay or default_delay(settings.api_key is not None)`. Close the price source if it has `close()`.
  - **Errors:** `StorageError` during pricing → `RunError` via `_run_error` (FR-025).
- [X] T021 [US1] Export `RunResult`, `PricingSummary`, `ImportSummary`, and `StopReason` from `src/monero_income/orchestration/__init__.py`, and remove `SyncResult`. Update `tests/integration/helpers.py` (`run_once` returns `RunResult`) and `tests/cli/test_cli_errors.py`.
- [X] T022 [US1] Update `src/monero_income/cli.py`:
  - add `--coingecko-api-key` and `--coingecko-api-key-type` (Typer `Option`, mapped onto `CliOptions`);
  - after the sync line, print `Priced N day(s) (M provisional).` when `priced > 0` (omit the parenthesis when M = 0), and `All transactions are valued.` when `all_final` (which is False when no transaction is recorded), using contracts/cli.md wording and singular forms.

  This makes T016 and T017 pass.
- [X] T023 [US1] Add an autouse fixture to `tests/conftest.py`, with a docstring explaining why. It monkeypatches `monero_income.orchestration.run.make_price_source` to return an empty `FakePriceSource()`, and `monero_income.orchestration.run._sleep` to a no-op, so no test can reach CoinGecko or sleep in real time, including feature 001's tests, whose runs now price after syncing. Then run the full suite: feature 001's tests must pass unchanged apart from T006 and T021.

**Checkpoint**: The MVP works. Transactions are valued exactly, provisional and final prices behave, and all gates are green.

---

## Phase 4: User Story 2 - Keep going through interruptions, outages, and rate limits (Priority: P2)

**Goal**: Paced requests, one retry on a 429, clean stops on price-source problems (with the
run still succeeding), and a failed run on storage errors. Covers FR-008 to FR-010, FR-023,
and FR-025, and SC-004, SC-005, SC-007, SC-010, and SC-011.

**Independent Test**: With 10 unpriced days and a source that fails after 4, the run records 4,
reports 6 with no price, and exits 0. The next run requests only the other 6.

### Tests for User Story 2 ⚠️ (write first, confirm they fail)

- [X] T024 [P] [US2] Write `tests/integration/test_pricing_failures.py` (a `tmp_path` database, the fakes). Cover:
  - **US2-1:** `PriceUnavailableError` on the 5th of 10 days → 4 prices kept, `no_price == 6`, `stopped.kind == "unavailable"`, no exception; the next run requests exactly the remaining 6.
  - **US2-2:** a 429 → `RecordingSleep` gets `10.0`, the same day is retried, and a second 429 stops the run with `rate_limited`, making 0 further requests (SC-011). A 429 with `retry_after=30` sleeps 30; `retry_after=120` is capped at 60.
  - **US2-3:** `KeyboardInterrupt` on the 3rd day propagates, 2 prices are kept, and the next run requests only the rest.
  - **US2-4:** with a key, consecutive requests are separated by `sleep` calls totalling ≥ 2.5 s; without a key, ≥ 6.0 s; with `min_request_delay = 2`, ≥ 2 s; and there's no sleep before the first request.
  - **US2-5:** a source unreachable from the start → `stopped.kind == "unavailable"` and the sync count is still returned.
  - **US2-6 / SC-010:** in every early stop, the max priced date is earlier than the min unpriced date.
  - **US2-7 / FR-025:** a storage write failure during `upsert_price` (patch `upsert_price` to raise `StorageWriteError`) → `RunError` containing `cannot write to database`, with earlier prices kept.
  - **FR-023:** a provisional day whose refresh fails keeps its price and is counted in `not_refreshed`.
  - **Key rejected:** `PriceKeyRejectedError` → `stopped.kind == "key_rejected"`.
  - **SC-005 equivalence:** for the US2-1 (unavailable) and US2-3 (`KeyboardInterrupt`) cases, after the follow-up run, `SELECT date_utc, usd_price, status FROM daily_prices ORDER BY date_utc` equals the same query on a fresh `tmp_path` database priced by one uninterrupted run on the same fake data. Both runs use the same fixed `FakeClock` time, so statuses are comparable.
- [X] T025 [P] [US2] Add to `tests/cli/test_cli_success.py`:
  - `N days still have no price; a later run will try again.`;
  - `N provisional prices couldn't be refreshed; a later run will try again.`;
  - for each `StopReason`, stderr shows the matching `Warning: price lookups stopped: …` line from contracts/cli.md, with exit 0, the key not shown, and no `Traceback`.

### Implementation for User Story 2

- [X] T026 [US2] Extend `price_days` in `src/monero_income/orchestration/pricing.py`:
  - **Pacing:** before every request except the first, sleep `max(0, delay - (clock() - last_request))`.
  - **Rate limit:** on `PriceRateLimitedError`, sleep `min(retry_after or 10, 60)` and retry the same day once; on a second 429, stop with `rate_limited`.
  - **Other source errors:** `PriceKeyRejectedError` → stop with `key_rejected`; `PriceUnavailableError` → stop with `unavailable` and the reason.
  - **On stop:** count the remaining requestable days into `no_price` or `not_refreshed`.
  - **Storage errors and `KeyboardInterrupt`:** propagate.

  This makes T024 pass.
- [X] T027 [US2] Update `src/monero_income/cli.py` to print the `no_price` and `not_refreshed` lines, and to send the stop warning through the reporter (`Warning: …`, stderr) with exit status 0. This makes T025 pass.

**Checkpoint**: US1 and US2 pass; price-source failures never fail a run, and storage failures always do

---

## Phase 5: User Story 3 - Days older than the price history (Priority: P2)

**Goal**: Days older than 364 days are never requested and are reported separately; a 401 with
error code 10012 is counted with them. Covers FR-011 and FR-012, and SC-006.

**Independent Test**: With days inside and outside the cutoff, only the inside days are
requested, and `too_old` counts the others.

### Tests for User Story 3 ⚠️ (write first, confirm they fail)

- [ ] T028 [P] [US3] Write `tests/integration/test_pricing_history.py`. Cover:
  - **US3-1 / SC-006:** with `FakeClock` at 2026-10-17, transaction days 2025-10-17 (365 days old) and 2025-10-18 (364 days old) → only 2025-10-18 is requested; `too_old == 1`.
  - **Aged-out provisional:** a provisional day older than the cutoff isn't requested, stays provisional, and is counted in `too_old`.
  - **10012 answer:** `OutsideHistory` for a day inside the cutoff → counted `too_old`, and the next (newer) day is still requested.
  - **US3-2:** `too_old`, `no_price`, and `not_refreshed` are reported as separate counts.
- [ ] T029 [P] [US3] Add to `tests/cli/test_cli_success.py`: `2 days are older than the price history and can't be looked up; use --import-prices to add them.` and its singular form.

### Implementation for User Story 3

- [ ] T030 [US3] Confirm `price_days` in `src/monero_income/orchestration/pricing.py` uses `plan_lookups(needs, today)` for the cutoff, adds the planned `too_old` days to the summary, and handles `OutsideHistory` without stopping. Add whatever T028 shows is missing.
- [ ] T031 [US3] Update `src/monero_income/cli.py` to print the `too_old` line. This makes T028 and T029 pass.

**Checkpoint**: US1–US3 pass

---

## Phase 6: User Story 4 - Import prices from a CSV file (Priority: P3, optional)

**Goal**: `--import-prices CSV` validates the whole file, imports final prices for old
unpriced days, skips and counts the rest, then pricing continues. Covers FR-019 and FR-020.

**Independent Test**: A five-row CSV (2 old unpriced days, 1 old priced day, 2 recent days) →
2 imported as final with source `import`, 3 skipped, and the 2 recent days priced by the
source.

### Tests for User Story 4 ⚠️ (write first, confirm they fail)

- [ ] T032 [P] [US4] Write `tests/unit/test_price_import_parse.py` for `parse_import(text) -> list[ImportRow]` (contracts/import-csv.md). Cover:
  - **Valid input:** a valid file with a BOM-free header; blank lines ignored; surrounding whitespace trimmed; `usd_price` kept exact (`"151.234"` → `Decimal("151.234")`).
  - **Rejected input:** each case raises `ImportFileError` naming the first bad line (header is line 1):
    - a header other than `date_utc,usd_price`;
    - an extra column;
    - a bad date such as `2024-13-01` or `2024-1-1`;
    - a missing price;
    - `0` or `-1`;
    - `1e2`, `NaN`, or `1,000.5`;
    - a duplicate date (`date 2024-03-01 already on line 4`).
  - **Selection:** `select_imports(rows, priced_days, cutoff)` keeps rows dated before the cutoff with no price and counts the rest as skipped.
- [ ] T033 [P] [US4] Write `tests/integration/test_price_import.py` (a `tmp_path` database and CSV file, the fakes, `CliOptions(import_prices=…)`). Cover:
  - **US4-1/2/3:** 2 imported with `status = 'final'` and `source = 'import'`, 3 skipped, the existing price unchanged, and the recent days requested from the source.
  - **US4-4:** a bad row on line 4 → `RunError` containing `cannot import prices from` and `line 4`; nothing imported, 0 price requests, the file bytes unchanged.
  - **US4-5:** importing again → `imported == 0`, every row skipped.
  - **US4-6:** a failed sync → no import and no lookups.
  - **Missing file:** a file that doesn't exist → `RunError`.
- [ ] T034 [P] [US4] Add to `tests/cli/test_cli_success.py`: `--import-prices PATH` maps onto `CliOptions`, and the line `Imported 2 prices; skipped 3 rows.` (with singular forms) comes before the pricing lines.

### Implementation for User Story 4

- [ ] T035 [US4] Implement `src/monero_income/primitives/price_import_file.py`:
  - `read_import_file(path: Path) -> str`, which opens with `encoding="utf-8-sig"` and turns an `OSError` into `ImportFileError(None, <reason>)`;
  - `parse_import(text: str) -> list[ImportRow]`, pure, using `csv.reader`, `date.fromisoformat` with an exact `YYYY-MM-DD` check, and a price regex `^[0-9]+(\.[0-9]+)?$` with value > 0.

  This makes the parse half of T032 pass.
- [ ] T036 [US4] Implement `src/monero_income/orchestration/price_import.py`:
  - `select_imports(rows, priced_days, cutoff) -> tuple[list[ImportRow], int]`, pure;
  - `import_prices(conn, path, *, today, clock) -> ImportSummary`, which reads, parses (validating the whole file before writing anything), selects using `priced_days` and `history_cutoff(today)`, and calls `insert_imported` with `DailyPrice(status="final", source="import", fetched_at=…)` in one transaction.
- [ ] T037 [US4] Update `run()` in `src/monero_income/orchestration/run.py`: after a successful sync and before `price_days`, call `import_prices` when `settings.import_prices` is set, and put the result in `RunResult.imported`. `ImportFileError` → `RunError(f"cannot import prices from {path}: {error}")`; storage errors go through `_run_error` (FR-020, FR-025).
- [ ] T038 [US4] Update `src/monero_income/cli.py`: add the `--import-prices` option and print the import line before the pricing lines. This makes T032–T034 pass.

**Checkpoint**: All four stories pass independently

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T039 [P] Extend `tests/cli/test_messages.py` if needed so the "transfer" scan covers the new orchestration modules. The glob already includes `orchestration/*.py`; confirm `pricing.py`, `price_import.py`, and `valuation.py` are scanned (FR-018).
- [ ] T040 [P] Add a test in `tests/integration/test_key_secrecy.py` (SC-008). Run with a distinctive API key from the config file and, separately, from `--coingecko-api-key` (through `CliRunner` with a monkeypatched price source) across every outcome: success, each `StopReason`, a storage error, and an invalid config. Assert the key appears in no stdout, stderr, exception text, or `repr`.
- [ ] T041 [P] Update the Usage section of `README.md` for pricing:
  - the new config keys, including `coingecko_api_key_type` (`demo`/`pro`), with a note that the config file is preferred over `--coingecko-api-key`;
  - the pricing output lines;
  - provisional and final prices;
  - the 364-day history limit, and `--import-prices` with the CSV format.

  Don't change the Intro or Status sections.
- [ ] T042 Run all gates and fix failures until all five pass with coverage ≥ 90%.
- [ ] T043 Run the manual checks in `specs/002-usd-valuation/quickstart.md` §2 against CoinGecko (with a Demo key, and once without a key), and record the results in the PR description. Don't commit any database files.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → stories → **Polish**.
- **Phase 2:** T002 and T003 first. T004 → T005 → T006. T007 → T008 (needs T005). T009 → T010. T011 needs T003. T012 → T013 → T014 (the fakes use the answer types).
- **US1 (Phase 3):** T015–T017 [P] → T018 → T019 → T020 → T021 → T022 → T023.
- **US2 (Phase 4):** depends on US1 (it extends `price_days` and `cli.py`). T024 and T025 [P] → T026 → T027.
- **US3 (Phase 5):** depends on US1, and is independent of US2's behavior. T028 and T029 [P] → T030 → T031.
- **US4 (Phase 6):** depends on US1 (`run()` and `RunResult`), and is independent of US2 and US3. T032–T034 [P] → T035 → T036 → T037 → T038.
- **Polish:** after the desired stories.

### Parallel Opportunities

- Phase 2: T002, T003, T004, T007, T009, T011, and T012 in parallel.
- US1 tests: T015–T017 together. US2, US3, and US4 test tasks can be written in parallel once US1 is merged.
- US3 and US4 can be implemented in parallel by different people; both edit `cli.py`, so coordinate that file.

---

## Parallel Example: User Story 1

```bash
Task: "T015 tests/adapters/test_price_source_http.py"
Task: "T016 tests/integration/test_pricing.py"
Task: "T017 tests/cli/test_cli_success.py additions"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 → Phase 2 (schema v2; all feature 001 tests green).
2. Phase 3 (US1): exact valuation with provisional and final prices.
3. **Stop and validate**: quickstart §2 "First run" with a Demo key.

### Incremental Delivery

US1 (valuation) → US2 (resilience and pacing, needed before pricing a full year in real use)
→ US3 (old-day reporting) → US4 (CSV import, optional) → Polish.

---

## Notes

- **Call-time defaults**: contracts/run-api.md specifies `None` defaults for `price_source_factory`, `clock`, and `sleep`, resolved at call time (T020), so the autouse test fixture (T023) can replace the real CoinGecko client and real sleep everywhere.
- **Renaming `SyncResult` to `RunResult`** touches feature 001's CLI and tests (T017, T021). No user-visible output changes for feature 001.
- **Commits**: commit after each task or logical group; never commit `.db` files or `config.toml`.
- **Analysis notes** (`/speckit-analyze`, 2026-10-17):
  - **G1** is no longer applicable: SC-012 was removed from the spec.
  - **G2** is resolved by the SC-005 equivalence case in T024.
  - **G3** is accepted with no new test: concurrent runs use the same storage layer and SQLite locking as feature 001, whose lock test (`tests/integration/test_concurrent_run.py`) already covers it, and the storage-error path during pricing is covered by US2-7 in T024.
  - **I1, I2, U1, U2** are resolved in contracts/run-api.md, data-model.md, T020, and contracts/cli.md with T007, T017, and T022.
