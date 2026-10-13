# Test Coverage — legacy `xmr-income-report`

Legacy repo @ `54e77b9`. Citations are `path:line` in that repo. (inferred) = not read directly.

## Suite facts

- 98 tests, all passing; 100% line coverage of measured code (verified: run with caches redirected outside the repo).
- `cli.py` is excluded from coverage (`pyproject.toml:31`), so the 100% excludes all orchestration and screen output.
- Coverage gate 90% (`pyproject.toml:27`).
- All external I/O is mocked: wallet (`tests/xmr_income_report/test_report.py:61-68`), price source (`tests/xmr_income_report/test_report.py:78-85`), HTTP (`tests/monero_tools/test_rpc.py:33`, `tests/monero_tools/test_coingecko.py:22-33`).
- DB tests use in-memory SQLite (`tests/monero_tools/test_db.py:22-29`, `tests/xmr_income_report/test_report.py:51-58`).
- No integration, end-to-end, or golden-file tests. No fixture data files.

## What is covered

### Wallet client — `tests/monero_tools/test_rpc.py`
- Returns `result` (`:33-45`).
- Payload method/params/version (`:48-68`).
- Empty params sent as `{}` (`:71-84`).
- No auth by default (`:92-99`).
- Auth object present when credentials are given; digest type not asserted (`:102-109`).
- JSON-RPC error → `RpcError` with code/message (`:117-131`).
- HTTP 403 → `HTTPError` (`:134-139`).
- Connection error propagates (`:142-147`).
- `RpcError` string form (`:155-160`).

### Price client — `tests/monero_tools/test_coingecko.py`
- Price returned as exact decimal (`:45-51`).
- Date sent as `DD-MM-YYYY` (`:54-61`).
- `localization=false` (`:64-70`).
- Other coin ids (`:73-78`).
- Missing `market_data` / `usd` → `PriceNotFoundError` (`:86-97`).
- 500 → `HTTPError`, not retried (`:100-104`, `:149-163`).
- 429 retried then succeeds (`:112-130`).
- 429 exhausts retries (`:133-146`).
- Backoff sequence 1, 2, 4, 8 (`:166-187`).
- Custom base URL (`:190-198`).
- API key header sent only when set (`:201-216`).
- Courtesy delay sleeps/skips (`:219-257`).

### Date keys — `tests/monero_tools/test_date_utils.py`
- ISO week padding, mid-month, year boundaries incl. `2025-W01` and `2019-W01` (`:14-37`).
- Month and year keys (`:45-71`).

### DB layer — `tests/monero_tools/test_db.py`
- Table creation idempotent (`:64-72`).
- Insert counts and duplicate-ignore for transfers and prices (`:78-106`, `:176-197`).
- Max height (`:109-125`).
- Clear helpers (`:131-170`).
- `update_price` (`:200-211`).
- Missing-price dates (`:214-231`).
- Left join keeps unpriced rows (`:237-253`).

### App logic — `tests/xmr_income_report/test_report.py`
- Config load/merge/precedence/defaults (`:93-163`).
- Sync: first run has no height filter (`:171-181`).
- Sync: stored shape incl. amount conversion and UTC date (`:194-209`).
- Sync: later runs filter by max height (`:217-234`).
- Sync: auth passthrough (`:242-255`).
- Sync: empty response (`:263-267`).
- Report rows: XMR, USD value, unpriced kept as none, Chicago local conversion in January, chronological sort, `since` filter (`:292-397`).
- Transaction CSV: file created; `txid`/`xmr`/`usd_value` values (`:405-449`).
- Monthly CSV: aggregation and sort (`:457-480`).
- `summarise`: weekly/monthly/yearly totals; empty input (`:488-525`).
- `fill_missing_prices`: no-op, success, `PriceNotFoundError`, `RequestException`, catch-and-continue, param passthrough (`:554-668`).

### CLI helpers — `tests/xmr_income_report/test_cli.py`
- `_parse_since` valid/none/invalid → exit 1 (`:59-81`).
- `_new_transfers` count, kwargs, exit 1 on error (`:89-121`).
- `_append_pricing` failed list, kwargs, exit 1 on error (`:129-162`).

## Gaps relevant to golden-file tests

### Whole-run output
- No test invokes the command end to end (`main`/`run`); `_open_database`, `_output_paths`, `_write_csvs`, `_print_summary`, `_print_table` are untested (`src/xmr_income_report/cli.py:80-210`).
- No test captures screen output: message text, colors, table layout, order of lines.
- No test of exit status for a full successful run, or for crashes (bad timezone, DB path, TOML).

### Transaction CSV
- Tests pass pre-formatted strings for `date_local`/`time_local` (`tests/xmr_income_report/test_report.py:410-411`, `:433-434`). Real rows hold date/time objects (`src/xmr_income_report/report.py:240-241`), so real formatting is untested.
- Header order, `usd_price`, `iso_week_local`, `month_local`, `year_local` cells: not asserted (`tests/xmr_income_report/test_report.py:446-449`).
- Unpriced row output (`usd_price` empty, `usd_value` `TBD`): untested.
- XMR formatting edge cases (whole numbers, scientific notation, 12-decimal amounts): untested.
- Line endings and encoding: untested.
- Rounding of half-cents: `money()` has no direct test (`src/xmr_income_report/report.py:262-263`).

### Monthly CSV and summaries
- Unpriced (`None`) values in monthly CSV and `summarise`: untested (`src/xmr_income_report/report.py:283`, `:324-326`).
- Sum-then-round vs round-then-sum difference: no test with half-cent cases.
- Screen table formatting (`$` prefix, `str()` XMR, sorting): untested.

### Time zone and calendar
- Only one time zone/date case: Chicago in January (`tests/xmr_income_report/test_report.py:318-327`).
- Untested:
  - daylight-saving transitions (spring gap, fall-back repeated hour);
  - local date ≠ UTC date (affects pricing day vs. listed day);
  - ISO week 53;
  - month/year boundaries after local conversion.
- `since` tested only away from day boundaries (`tests/xmr_income_report/test_report.py:352-378`); the UTC-vs-local boundary case is untested.
- Some fixtures use float timestamps (`tests/xmr_income_report/test_report.py:334`, `:338`); the wallet supplies integers (inferred).

### Sync realism
- No test of multiple wallet entries for one txid (multi-subaddress) (`src/monero_tools/db.py:103`).
- No test of wallet `min_height` semantics or a real wallet response shape; mocks return only the fields used (`tests/xmr_income_report/test_report.py:43-48`).
- No test of missing `in` key in the wallet response (`src/xmr_income_report/report.py:150`).

### Determinism
- `test_db.py` uses unseeded Faker (`tests/monero_tools/test_db.py:16`). Random dates/amounts make failures non-reproducible.
- Faker amounts come from floats (`tests/monero_tools/test_db.py:41-43`, `:55-57`), so they don't exercise true 12-decimal values.
- Report row order for equal timestamps is not defined (`src/xmr_income_report/report.py:253`); a golden file would need a tie-breaker.
- Screen output width depends on the terminal (inferred: `rich`); golden tests need a fixed width and color disabled.
- Default timezone and output directory come from config/CWD (`src/xmr_income_report/report.py:83-84`); the config path is fixed under the home directory (`src/xmr_income_report/report.py:35`). Golden runs need these isolated.

### Suggested golden fixtures (from gaps above)
- Priced + unpriced mix in one month.
- Amounts: whole, 1 atomic unit, max 12 decimals.
- Half-cent rounding cases, per row and per month.
- Transactions near UTC midnight in a non-UTC zone.
- DST start/end, including the repeated hour.
- ISO week 53 and year-boundary weeks.
- Months with no transactions between active months.
- Two transactions with identical timestamps.
- Empty database.
