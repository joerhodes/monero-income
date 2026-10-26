# Data Model: Transaction CSV Export

**Feature**: 003-transaction-csv-export | **Date**: 2026-10-26

## Persistent schema

**Unchanged.** The export reads feature 001's `transactions` table and feature 002's
`daily_prices` table, and writes nothing to the database (FR-024). No migration.

Read query (one statement, read-only):

```sql
SELECT t.txid, t.height, t.amount_piconero, t.occurred_at, p.usd_price, p.status
FROM transactions AS t
LEFT JOIN daily_prices AS p ON p.date_utc = t.occurred_date
```

`occurred_date` is the UTC date of `occurred_at` (a generated column), so the join gives each
transaction its UTC day's price, or `NULL`s when that day has none.

## The export file

See [contracts/export-csv.md](contracts/export-csv.md) for the byte-level format.

| Property | Value |
|----------|-------|
| Path | `<reports directory>/xmr_income.csv` |
| Mode | `0o600` (owner read/write only), every write (FR-026) |
| Lifecycle | Absent until the first successful run; then replaced in full by each successful run; never partial (FR-006, FR-007) |
| Temporary file | `<reports directory>/.xmr_income.csv.<random>.tmp`, mode `0o600`; exists only during a write; removed on failure, or by the next write if a crash left it (research R3) |

## In-memory types

All frozen dataclasses. Amounts are `int` piconero and prices `Decimal`; never `float`.

### `ExportRecord` (primitives/models.py): one transaction with its day's price, as read

| Field | Type | From |
|-------|------|------|
| `txid` | `str` | `transactions.txid` |
| `height` | `int` | `transactions.height` |
| `amount_piconero` | `int` | `transactions.amount_piconero` |
| `occurred_at` | `int` | `transactions.occurred_at` (UTC Unix seconds) |
| `usd_price` | `Decimal \| None` | `daily_prices.usd_price` text → `Decimal`; `None` if no price |
| `price_status` | `Literal["provisional", "final"] \| None` | `daily_prices.status`; `None` if no price |

`usd_price` and `price_status` are both set or both `None`. A stored price that doesn't parse as
a positive `Decimal` is a storage read error (it can't happen through this tool's writes).

### `ExportSummary` (orchestration/export.py): what the run reports

| Field | Type | Meaning |
|-------|------|---------|
| `path` | `Path` | Absolute path of the export written |
| `transactions` | `int` | Data rows written (FR-021) |

### `RunResult` (orchestration/run.py): gains one field

| Field | Type | Meaning |
|-------|------|---------|
| `exported` | `ExportSummary \| None` | Set by every successful `run()`; `None` only as the default, so existing test constructions keep working |

### `Settings` / `CliOptions` (orchestration/settings.py)

| Type | New field | Type | Default |
|------|-----------|------|---------|
| `CliOptions` | `reports_path` | `str \| None` | `None` (not given) |
| `Settings` | `reports_path` | `Path` | `~/reports`, `~` expanded at resolve time |

## Pure transformations (orchestration/export_format.py)

Each takes plain values and returns plain values, with no I/O (constitution IV).

| Function | Input → output | Rule |
|----------|----------------|------|
| `HEADER` | constant | `("txid", "height", "timestamp_utc", "xmr", "usd_price", "price_status", "usd_value")` |
| `format_timestamp` | `int` → `str` | `YYYY-MM-DDTHH:MM:SSZ` in UTC (FR-013) |
| `format_xmr` | `int` piconero → `str` | Exactly 12 decimals, integer arithmetic (FR-014) |
| `format_price` | `Decimal \| None` → `str` | `format(price, "f")`, or `TBD` (FR-015) |
| `round_cents` | `Decimal` → `Decimal` | `quantize(Decimal("0.01"), ROUND_HALF_UP)` with a local context wide enough for the value (research R4) |
| `format_usd_value` | `(int, Decimal \| None)` → `str` | `format(round_cents(usd_value(amount, price)), "f")`, or `TBD` (FR-017) |
| `export_rows` | `Sequence[ExportRecord]` → `list[tuple[str, ...]]` | Sorted by `(occurred_at, height, txid)` (FR-010), one 7-tuple per record, columns in `HEADER` order |

`usd_value` is feature 002's exact product (`orchestration/valuation.py`), reused unchanged.

## Primitives

| Module | Function | Kind | Behavior |
|--------|----------|------|----------|
| `primitives/export_db.py` | `export_records(conn) -> list[ExportRecord]` | I/O (read) | Runs the query above; `sqlite3.Error` → `StorageReadError` |
| `primitives/export_file.py` | `write_export(directory, name, header, rows) -> Path` | I/O (write) | Creates the directory; locks it; removes stale temporaries; writes a `0o600` temporary file, `fsync`s it, `os.replace`s it, `fsync`s the directory; returns the final path. `OSError` → `ExportWriteError`; any other exception removes the temporary file and propagates |

New error: `ExportWriteError(Exception)` in `primitives/errors.py`. Its message is the OS
reason (`strerror`); it never includes file contents.

## State: export file per run

| Run outcome | Export afterwards |
|-------------|-------------------|
| Invalid settings, sync failure, storage error, invalid import file | Unchanged (previous, or absent) |
| Sync and pricing complete, write succeeds | Replaced by the complete new export, mode `0o600` |
| Sync and pricing complete, write fails (`ExportWriteError`) | Unchanged; run exits 1 |
| Interrupted (Ctrl-C) during the write | Unchanged; temporary file removed; run exits 130 |
| Killed (`SIGKILL`, power loss) during the write | Unchanged; temporary file may remain until the next write removes it |
