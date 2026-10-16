# Implementation Facts — legacy `xmr-income-report`

Source: legacy repo `xmr-income-report`, branch `v.0.3`, commit `54e77b9`.
Citations are `path:line` relative to that repo root.
Items marked (inferred) were not read directly from this code.
Config values are not reproduced; only keys and purpose.

## 1. Runtime and dependencies

- Python 3.12 pinned (`.python-version:1`); `requires-python >=3.12` (`pyproject.toml:6`).
- Runtime deps: `typer`, `rich`, `requests >= 2.32` (`pyproject.toml:7-11`).
- Locked versions: typer 0.26.7 (`uv.lock:335-336`), rich 15.0.0 (`uv.lock:313-314`), requests 2.34.2 (`uv.lock:298-299`).
- Dev deps: faker, pytest, pytest-cov (`pyproject.toml:18-23`); locked faker 40.36.0, pytest 9.0.3, pytest-cov 7.1.0 (`uv.lock:190-191`, `uv.lock:268-269`, `uv.lock:284-285`).
- Stdlib relied on: `sqlite3`, `decimal`, `tomllib`, `zoneinfo`, `csv` (`src/xmr_income_report/report.py:9-15`).
- Build backend `uv_build`; both packages shipped (`pyproject.toml:36-41`).
- Package/tooling managed with `uv` (`README.md:18`, `README.md:26`).
- Package version string is `0.1.0` (`pyproject.toml:3`).

## 2. Package layout

- `src/` layout with two packages (`pyproject.toml:41`):
  - `monero_tools` — reusable library: `rpc.py` (wallet JSON-RPC client), `coingecko.py` (price lookup), `db.py` (SQLite schema + queries), `date_utils.py` (week/month/year keys).
  - `xmr_income_report` — app: `cli.py` (Typer entry point, orchestration, screen output), `report.py` (config, sync, pricing, row shaping, CSV, aggregation).
- Console script `xmr-income-report` → `xmr_income_report.cli:app` (`pyproject.toml:13-14`).
- `main.py` at repo root is an unused hello-world stub (`main.py:1-6`).
- Tests mirror packages: `tests/monero_tools/*`, `tests/xmr_income_report/*`; no `conftest.py`, no fixture data files.
- `db.py` is designed to be shared with other tools; callers own the connection and file path (`src/monero_tools/db.py:4-9`).

## 3. Database

- Engine: SQLite via `sqlite3.connect(db_path)`; rows returned as `sqlite3.Row` (`src/monero_tools/db.py:18-30`).
- Default file: `~/.local/share/xmr-income-report/xmr.db` (`src/xmr_income_report/report.py:36`). Parent directory is not created by the code (`src/monero_tools/db.py:28`); first run fails if it does not exist (verified by probe).
- Overridable via `--db-path` or config key `db_path` (`src/xmr_income_report/cli.py:48`, `src/xmr_income_report/report.py:85`).

### Table `transfers` (`src/monero_tools/db.py:43-53`)

| Column | Type | Constraint | Meaning |
|---|---|---|---|
| `txid` | TEXT | PRIMARY KEY | wallet transaction id |
| `height` | INTEGER | NOT NULL | block height |
| `timestamp` | INTEGER | NOT NULL | Unix epoch seconds (UTC) from wallet |
| `amount_xmr` | TEXT | NOT NULL | `str(Decimal)` of XMR amount (`src/monero_tools/db.py:95`) |
| `date_utc` | TEXT | NOT NULL | `YYYY-MM-DD` UTC date derived from `timestamp` (`src/xmr_income_report/report.py:102`, `:109`) |

### Table `prices` (`src/monero_tools/db.py:64-71`)

| Column | Type | Constraint | Meaning |
|---|---|---|---|
| `date_utc` | TEXT | PRIMARY KEY | `YYYY-MM-DD` UTC day |
| `usd_price` | TEXT | NOT NULL | `str(Decimal)` USD per 1 coin (`src/monero_tools/db.py:152`) |

- Relationship: join on `date_utc`; no foreign key (`src/monero_tools/db.py:222-229`).
- No secondary indexes; only the two primary keys.
- Migrations: none. Tables created with `CREATE TABLE IF NOT EXISTS` on every run (`src/xmr_income_report/cli.py:105-112`). No schema version is stored.
- Writes: `INSERT OR IGNORE` + one `commit` per batch (`src/monero_tools/db.py:103-104`, `:156-157`). Inserted count = `COUNT(*)` after minus before (`src/monero_tools/db.py:101-107`).
- Pricing inserts one row per call, so each price commits independently (`src/xmr_income_report/report.py:199`).
- Unused by the app: `clear_transfers_table`, `update_price`, `clear_prices_table` (`src/monero_tools/db.py:125-134`, `:163-176`, `:196-205`).
- Report query: `transfers LEFT JOIN prices` on `date_utc`, no `ORDER BY` (`src/monero_tools/db.py:222-229`).
- Missing-price query: distinct `date_utc` in transfers not in prices, no `ORDER BY` (`src/monero_tools/db.py:190-193`).

## 4. Wallet RPC

- Transport: HTTP POST of JSON-RPC 2.0 body `{"jsonrpc":"2.0","id":"0","method":…,"params":…}` (`src/monero_tools/rpc.py:46-60`).
- Timeout: 20 s, fixed (`src/monero_tools/rpc.py:26`); not configurable from CLI/config (`src/xmr_income_report/report.py:144-149`).
- Auth: HTTP Digest, only when username is non-empty (`src/monero_tools/rpc.py:53`, `src/xmr_income_report/report.py:142`). Password without username is ignored.
- Endpoint: full URL from `--rpc-url` / config `rpc_url`; default is a loopback `http` endpoint on port 18088, path `/json_rpc` (`src/xmr_income_report/report.py:79-80`).
- Errors raised:
  - non-2xx → `requests.HTTPError` (`src/monero_tools/rpc.py:61`)
  - JSON-RPC `error` object → `RpcError` with text `RPC error {code}: {message}` (`src/monero_tools/rpc.py:12-18`, `:65-67`)
  - missing `result` → `KeyError` (`src/monero_tools/rpc.py:69`)
  - network failure → `requests.RequestException` (`src/monero_tools/rpc.py:44`)
- No retries.

### Call made: `get_transfers` (`src/xmr_income_report/report.py:131-149`)

| Param | Value |
|---|---|
| `in` | true |
| `out` | false |
| `pending` | false |
| `failed` | false |
| `pool` | false |
| `filter_by_height` | true — only when ≥1 transfer is recorded |
| `min_height` | `MAX(height)` of recorded transfers — only when ≥1 recorded |

- Checkpoint is `MAX(height)` (`src/monero_tools/db.py:121-122`). Whether the wallet treats `min_height` as inclusive or exclusive is not handled by the code; monero-wallet-rpc treats it as exclusive (inferred, from monero-wallet-rpc behavior).
- Response: `result["in"]`, defaulting to `[]` when absent (`src/xmr_income_report/report.py:150`).
- One RPC call per run; the full list is held in memory (`src/xmr_income_report/report.py:144-152`).

### Response → record (`src/xmr_income_report/report.py:101-110`)

| Record field | Source |
|---|---|
| `txid` | `entry["txid"]` |
| `height` | `entry["height"]` |
| `timestamp` | `entry["timestamp"]` unchanged |
| `amount_xmr` | `Decimal(entry["amount"]) / 1e12` (`ATOMIC_UNITS`, `report.py:34`) |
| `date_utc` | UTC date of `timestamp`, `%Y-%m-%d` |

- All other entry fields are ignored (e.g. subaddress index, type, fee, unlock time) (inferred field list, from monero-wallet-rpc docs).
- Duplicate `txid` entries in one response: first wins, rest silently dropped by `INSERT OR IGNORE` (`src/monero_tools/db.py:103`; verified by probe).

## 5. Price API (CoinGecko)

- Endpoint: `GET {base_url}/coins/{coin_id}/history` (`src/monero_tools/coingecko.py:62`).
- Query: `date=DD-MM-YYYY`, `localization=false` (`src/monero_tools/coingecko.py:61`, `:63`).
- Header: `x-cg-pro-api-key: <key>` only when key non-empty (`src/monero_tools/coingecko.py:64`).
- Timeout: 20 s per request (`src/monero_tools/coingecko.py:75`).
- Price path: `market_data.current_price.usd`, converted via `Decimal(str(value))` (`src/monero_tools/coingecko.py:87`).
- Defaults: base URL = CoinGecko public v3 API, coin `monero`, no key (`src/xmr_income_report/report.py:87-90`).
- One `requests.Session` reused for all lookups in a run (`src/xmr_income_report/cli.py:148`).
- One lookup per distinct UTC date lacking a price (`src/xmr_income_report/report.py:182-201`).

### Rate limiting and errors

- Courtesy delay: ≥ `min_request_delay` s between requests (default 1.2) using a module-global timestamp (`src/monero_tools/coingecko.py:19`, `:70-73`; `src/xmr_income_report/report.py:91`).
- HTTP 429: sleep `backoff_base ** attempt` (2.0 → 1, 2, 4, 8, 16 s), retry up to `max_retries` = 5 total attempts (`src/monero_tools/coingecko.py:31-33`, `:68-81`).
- After the last 429: raise `HTTPError("Rate limited after 5 retries for '<coin>' on <date>")` (`src/monero_tools/coingecko.py:95-97`).
- Other non-2xx: raise immediately, no retry (`src/monero_tools/coingecko.py:83`).
- Missing price keys / null data: `PriceNotFoundError("No USD price found for '<coin>' on <date>")` (`src/monero_tools/coingecko.py:86-91`).
- Caller catches `PriceNotFoundError` and `RequestException` per date, records the date as failed, continues (`src/xmr_income_report/report.py:200-201`).
- Any other exception escapes to CLI → error message, exit 1 (`src/xmr_income_report/cli.py:159-161`).

## 6. Configuration

- Format: TOML, read with `tomllib` (`src/xmr_income_report/report.py:65-66`).
- Location: `~/.config/xmr-income-report/config.toml`, fixed; no flag to change it (`src/xmr_income_report/report.py:35`, `src/xmr_income_report/cli.py:59`).
- Missing file → all defaults (`src/xmr_income_report/report.py:63-64`). Malformed TOML → unhandled exception (inferred: `tomllib.TOMLDecodeError` is not caught at `src/xmr_income_report/cli.py:59`).
- Template `config.toml.example` documents all keys except `db_path`.
- Precedence: CLI flag > config > built-in default; empty string / falsy counts as unset (`src/xmr_income_report/report.py:78-92`).

| Key | Section | CLI flag | Purpose | Code default (`report.py`) |
|---|---|---|---|---|
| `rpc_url` | top | `--rpc-url` | wallet JSON-RPC URL | loopback, port 18088, `/json_rpc` (`:79-80`) |
| `username` | top | `--username` | wallet RPC digest-auth user | empty (`:81`) |
| `password` | top | `--password` | wallet RPC digest-auth password | empty (`:82`) |
| `timezone` | top | `--timezone` | IANA zone for local dates/grouping | `America/Chicago` (`:83`) |
| `output_dir` | top | `--output-dir` | CSV output directory | `.` (`:84`) |
| `db_path` | top | `--db-path` | SQLite file | `~/.local/share/xmr-income-report/xmr.db` (`:85`, `:36`) |
| `base_url` | `[coingecko]` | `--coingecko-url` | price API base URL | public v3 API (`:87-88`) |
| `api_key` | `[coingecko]` | `--coingecko-key` | price API key | empty (`:89`) |
| `coin_id` | `[coingecko]` | `--coin-id` | price API coin id | `monero` (`:90`) |
| `min_request_delay` | `[coingecko]` | — (config only) | seconds between price requests | 1.2 (`:91`) |
| — | — | `--since` | report start date (CLI only) | none (`:86`) |

## 7. CLI

- Single Typer command; no subcommands (`src/xmr_income_report/cli.py:31-38`).
- Help: "Summarize Monero mining income by week/month using wallet RPC + USD historical prices." (`src/xmr_income_report/cli.py:32`).
- Flags (all optional strings): `--rpc-url`, `--username`, `--password`, `--timezone`, `--output-dir`, `--db-path`, `--since`, `--coingecko-url`, `--coingecko-key`, `--coin-id` (`src/xmr_income_report/cli.py:39-56`).
- `--since`: parsed with `date.fromisoformat` (`src/xmr_income_report/cli.py:96-99`); accepts any ISO 8601 date form Python 3.12 accepts, e.g. `20240115`, `2024-W03-1` (verified by probe).

### Run order (`src/xmr_income_report/cli.py:59-89`)

1. Load config, merge flags (`:59-74`).
2. Validate `--since` (`:76`).
3. Open DB, create tables (`:84`).
4. Sync transfers (`:85`).
5. Fill missing prices (`:86`).
6. Build report rows with `--since` filter and timezone (`:87`).
7. Write both CSVs (`:88`).
8. Print weekly, monthly, yearly tables and failed-price warning (`:89`).

### Exit codes

| Code | When | Cite |
|---|---|---|
| 0 | normal completion, including when some prices failed | `cli.py:80-89` |
| 1 | invalid `--since` | `cli.py:100-102` |
| 1 | any exception during sync | `cli.py:135-137` |
| 1 | non-caught exception during pricing | `cli.py:159-161` |
| 1 + traceback | DB open error, bad TOML, unknown timezone, CSV write error (inferred: uncaught exception) | `cli.py:59`, `:84`, `:87`, `:88` |
| 2 | unknown flag / usage error (inferred: Typer/Click convention) | — |

### User-facing messages (rich markup stripped)

| Text | When | Cite |
|---|---|---|
| `Invalid date format for --since: {value}` (red) | bad `--since` | `cli.py:101` |
| `Error fetching transfers: {exception text}` | sync failure | `cli.py:136` |
| `No new transfers found.` (yellow) | sync inserted 0 rows | `cli.py:139-140` |
| `Fetched {n} new prices.` (green) | pricing finished, always | `cli.py:158` |
| `Error looking up USD prices: {exception text}` | pricing failure | `cli.py:160` |
| `Wrote {transactions csv path}` / `Wrote {monthly csv path}` | after CSV writes | `cli.py:173-174` |
| tables `Weekly Summary`, `Monthly Summary`, `Yearly Summary` | always | `cli.py:184-188` |
| `Failed to fetch prices for {n} transaction dates.` (yellow) | ≥1 date failed | `cli.py:190-193` |
| `RPC error {code}: {message}` | inside sync error text | `rpc.py:18` |

- No message reports how many new transfers were recorded (`src/xmr_income_report/cli.py:139-141`, return value unused at `:85`).

## 8. CSV and summary computation

### Report rows (`src/xmr_income_report/report.py:211-254`)

- `local_dt` = UTC timestamp converted to configured zone (`:230-231`).
- `--since` filter: drop rows whose **UTC** date < since (`:232-233`).
- `xmr` = `Decimal(amount_xmr)` (`:235`).
- `usd_price` = `Decimal(prices.usd_price)` or `None` (`:236`).
- `usd_value` = `xmr * usd_price` unrounded, or `None` (`:237`); default Decimal context (28 significant digits).
- Week key `YYYY-Www` from ISO calendar of local datetime (`src/monero_tools/date_utils.py:26-27`); month `YYYY-MM` (`:44`); year `YYYY` (`:61`).
- Sorted by `(date_local, time_local)` only (`:253`).

### `xmr_income.csv` (`src/xmr_income_report/report.py:266-272`)

- Path `{output_dir}/xmr_income.csv`; dir created with parents (`src/xmr_income_report/cli.py:119-121`).
- Opened `"w"`, `newline=""`, no explicit encoding (`report.py:268`). Python `csv` default line terminator `\r\n` (inferred).
- Columns, in order: `date_local, time_local, txid, height, xmr, usd_price, usd_value, iso_week_local, month_local, year_local` (`report.py:37-48`).
- Cell formatting:
  - `date_local` — `str(date)` → `YYYY-MM-DD`
  - `time_local` — `str(time)` → `HH:MM:SS`
  - `xmr` — `str(Decimal)`: no trailing zeros, `2` for whole amounts, scientific for tiny amounts, e.g. `1E-7` (verified by probe)
  - `usd_price` — `str(Decimal)`, e.g. `150.0`; empty when unpriced (verified by probe)
  - `usd_value` — `money()`: ROUND_HALF_UP to `0.01`; `TBD` when unpriced (`report.py:262-263`, `:272`)

### `xmr_income_monthly.csv` (`src/xmr_income_report/report.py:275-295`)

- Path `{output_dir}/xmr_income_monthly.csv` (`src/xmr_income_report/cli.py:121`).
- Columns: `month, xmr, usd_value` (`report.py:286`).
- One row per `month_local` present in rows; sorted ascending; months without transactions omitted (`report.py:278-288`).
- `xmr` = exact sum, `str(Decimal)` (`report.py:282`, `:292`).
- `usd_value` = sum of unrounded per-row values (unpriced add 0), then `money()` once (`report.py:283`, `:293`).

### Screen summaries (`src/xmr_income_report/report.py:303-327`, `src/xmr_income_report/cli.py:177-210`)

- Weekly (ISO week), monthly, yearly buckets from local-time keys (`report.py:315-320`).
- Per bucket: exact XMR sum; USD sum of unrounded values, unpriced add 0 (`report.py:323-326`).
- Rendered as `rich` tables with columns `Period`, `XMR`, `USD Value`; sorted by key; XMR via `str()`, USD via `$` + `money()` (`cli.py:196-210`).
- Monthly screen totals use the same logic as the monthly CSV.
