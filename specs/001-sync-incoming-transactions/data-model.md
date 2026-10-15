# Data Model: Sync Incoming Wallet Transactions

**Feature**: 001-sync-incoming-transactions | **Date**: 2026-10-14

## Persistent schema (SQLite, schema version 1)

Tracked with `PRAGMA user_version`. Version 0 means an empty, newly created file; migration
`0 → 1` creates everything below in one transaction.

### Table `transactions`

One row per recorded incoming transaction (FR-005, FR-008).

| Column | Type | Constraints | Source / meaning |
|--------|------|-------------|------------------|
| `txid` | `TEXT` | `PRIMARY KEY`, `CHECK (length(txid) = 64)` | Wallet `txid`, lowercase hex |
| `height` | `INTEGER` | `NOT NULL`, `CHECK (height > 0)` | Wallet `height`: the block that included it |
| `amount_piconero` | `INTEGER` | `NOT NULL`, `CHECK (amount_piconero > 0)` | Sum of wallet `amount` over all entries with this txid, in atomic units, exactly as reported |
| `occurred_at` | `INTEGER` | `NOT NULL` | Wallet `timestamp`: UTC Unix seconds |
| `occurred_date` | `TEXT` | `GENERATED ALWAYS AS (date(occurred_at, 'unixepoch')) STORED` | UTC calendar date `YYYY-MM-DD`, for later pricing |

Index: `transactions_height_idx` on `height` (finding the last recorded height).

Rows are only ever inserted, never updated or deleted (FR-009, constitution VI). Inserts use
plain `INSERT`. A primary-key conflict can only come from a concurrent run and is reported as
a storage error, with the whole batch rolled back.

### Table `meta`

Key-value settings that belong to the database rather than to a transaction.

| Column | Type | Constraints |
|--------|------|-------------|
| `key` | `TEXT` | `PRIMARY KEY` |
| `value` | `TEXT` | `NOT NULL` |

Keys used by this feature:

| Key | Value | Written | Meaning |
|-----|-------|---------|---------|
| `since` | `YYYY-MM-DD` | Once, in the same transaction that creates the schema, only if a start date was given | Start date (FR-020). Absent means no start date. |

## In-memory types

All are frozen dataclasses. Amounts are `int` piconero (see the constitution check in
`plan.md`), never `float`.

### `IncomingEntry` (primitives): one wallet `in` entry, parsed

| Field | Type | From wallet field |
|-------|------|-------------------|
| `txid` | `str` | `txid` |
| `height` | `int` | `height` |
| `amount_piconero` | `int` | `amount` |
| `timestamp` | `int` | `timestamp` |

Parsing rejects (as a wallet response error) a missing field, a wrong JSON type (including a
JSON float where an integer is expected), a negative number, or a txid that isn't 64 hex
characters.

### `TransactionRecord` (primitives): one row to store

| Field | Type |
|-------|------|
| `txid` | `str` |
| `height` | `int` |
| `amount_piconero` | `int` |
| `occurred_at` | `int` (UTC Unix seconds) |

### `Settings` (orchestration): resolved run settings

| Field | Type | Default | Validation |
|-------|------|---------|------------|
| `rpc_url` | `str` | `http://127.0.0.1:18088/json_rpc` | Scheme `http` or `https`, has a host, **no user info** (`user:pass@`) |
| `username` | `str \| None` | `None` | Non-empty if given |
| `password` | `str \| None` | `None` | From the config file only. Set without `username` → error (FR-018). |
| `db_path` | `Path` | `~/.local/share/monero-income/xmr.db` | `~` expanded |
| `since` | `date \| None` | `None` | ISO `YYYY-MM-DD`. TOML date literal or string in the config file. |

Precedence per field: command-line option, then config file, then default. A username without
a password is allowed; digest auth is attempted with an empty password, and the wallet
decides.

### `SyncResult` (orchestration)

| Field | Type | Meaning |
|-------|------|---------|
| `recorded` | `int` | Number of new transactions inserted by this run (FR-012) |

## Pure transformations (orchestration)

Each takes plain values and returns plain values, with no I/O (constitution IV).

| Function | Input → output | Rule |
|----------|----------------|------|
| `fetch_windows(start_after, wallet_height)` | `int, int → list[tuple[int, int]]` | Consecutive `(lo, hi]` windows of 100,000 blocks covering `start_after < h <= wallet_height` |
| `first_window_start(last_height)` | `int \| None → int` | `None → 0`; else `max(last_height - 61, 0)` (60-block overlap, inclusive; `min_height` is exclusive) |
| `discard_before(entries, since)` | `→ list[IncomingEntry]` | Keep `timestamp >= since 00:00:00 UTC`; no-op when `since` is `None` |
| `combine_by_txid(entries)` | `→ list[TransactionRecord]` | One record per txid; amounts summed; height/timestamp from the entries (identical per txid) |
| `select_new(records, recorded_txids)` | `→ list[TransactionRecord]` | Drop records already stored |
| `check_since(given, saved, is_new_db)` | `→ date \| None` or error | New DB: the given date. Existing DB: given must be `None` or equal to saved; otherwise a mismatch error. |
| `resolve_settings(cli, file, defaults)` | `→ Settings` or error | Precedence and validation above |
| `is_readable_by_others(mode)` | `int → bool` | `mode & 0o004` |

## Run lifecycle

```text
resolve settings ── invalid ──▶ error (nothing touched)
      │
open database ── unreadable / newer schema ──▶ error (file untouched)
      │  missing → create parent dir + schema v1 + meta.since   (one transaction)
      │  exists  → migrate to v1 if older                        (one transaction)
check start date ── mismatch ──▶ error (nothing recorded)
      │
read last height ─▶ get_height ─▶ fetch windows (in only) ── any wallet error ──▶ error
      │                                                         (nothing recorded)
transform: discard before since → combine → select new
      │
insert new records (one transaction) ─▶ SyncResult(recorded = n)
```

An interruption anywhere before the final commit leaves the database exactly as it was before
the run, apart from a newly created empty database. An interruption during the commit is
handled by SQLite's atomic commit.
