# Data Model: USD Valuation

**Feature**: 002-usd-valuation | **Date**: 2026-10-17

## Persistent schema: version 1 → 2

Migration step 2 adds one table and two triggers; table `transactions` (feature 001) is
unchanged. It is tested from a version-1 database with rows (constitution VI: from every
prior released schema).

### Table `daily_prices`

| Column | Type | Constraints | Meaning |
|--------|------|-------------|---------|
| `date_utc` | `TEXT` | `PRIMARY KEY`, `CHECK (date_utc GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')` | UTC calendar date, matches `transactions.occurred_date` |
| `usd_price` | `TEXT` | `NOT NULL` | USD per 1 XMR as plain decimal text (no exponent), lossless; positive (checked in code) |
| `status` | `TEXT` | `NOT NULL`, `CHECK (status IN ('provisional', 'final'))` | FR-021 |
| `source` | `TEXT` | `NOT NULL`, `CHECK (source IN ('api', 'import'))` | Where the price came from |
| `fetched_at` | `INTEGER` | `NOT NULL` | UTC Unix seconds when looked up or imported |

Triggers (defense in depth for FR-006 and constitution VI):

- `daily_prices_final_no_update`: `BEFORE UPDATE ON daily_prices WHEN OLD.status = 'final'`
  → `RAISE(ABORT, 'final price is immutable')`.
- `daily_prices_no_delete`: `BEFORE DELETE ON daily_prices` → `RAISE(ABORT, ...)`.

Writes:

- **Looked-up price**: `INSERT … ON CONFLICT(date_utc) DO UPDATE SET usd_price, status,
  source, fetched_at WHERE daily_prices.status = 'provisional'`. One price, one commit, so an
  interruption keeps every recorded price (FR-008).
- **Imported prices**: plain `INSERT` of pre-filtered rows in one transaction. Any conflict is
  a storage write error and rolls back the whole import.

Transaction USD values are **not stored**. They are computed from `amount_piconero` and the
day's `usd_price` when needed (decided).

## In-memory types

| Type | Layer | Fields |
|------|-------|--------|
| `DailyPrice` | primitives | `date_utc: date`, `usd_price: Decimal`, `status: Literal["provisional", "final"]`, `source: Literal["api", "import"]`, `fetched_at: int` |
| `PriceNeed` | primitives | `date_utc: date`, `has_provisional: bool` (one row per transaction day without a final price) |
| `ImportRow` | primitives | `line: int`, `date_utc: date`, `usd_price: Decimal` |
| `PricingSummary` | orchestration | `priced: int`, `provisional: int`, `no_price: int`, `not_refreshed: int`, `too_old: int`, `all_final: bool`, `stopped: StopReason \| None` |
| `ImportSummary` | orchestration | `imported: int`, `skipped: int` |
| `RunResult` | orchestration | `recorded: int`, `imported: ImportSummary \| None`, `pricing: PricingSummary` (replaces feature 001's `SyncResult`) |
| `StopReason` | orchestration | `rate_limited`, `key_rejected`, `unavailable` (with the reason text, never the key) |

`Settings` gains:

- `coingecko_url: str`, defaulting by key type: `pro` → `https://pro-api.coingecko.com/api/v3`,
  otherwise `https://api.coingecko.com/api/v3`;
- `coin_id: str`, default `monero`;
- `api_key: str | None`, hidden from `repr`;
- `api_key_type: Literal["demo", "pro"] | None`, required when `api_key` is set, otherwise
  `None`;
- `min_request_delay: Decimal | None`, in seconds, ≥ 0; `None` means the R1 default.

`CliOptions` gains `import_prices: str | None`, `coingecko_api_key: str | None` and
`coingecko_api_key_type: str | None`. Command-line options override the config file.

## Pure functions (orchestration)

| Function | Rule |
|----------|------|
| `history_cutoff(today)` | `today - 364 days`. A day is requestable when `day >= cutoff` |
| `plan_lookups(needs, today)` | Split into `requestable` (oldest first, FR-024) and `too_old` (FR-011; includes provisional days that aged out) |
| `settled_at(day)` | `datetime(day + 1 day, 00:00 UTC) + 1 hour` |
| `price_status(day, now)` | `"final"` if `now >= settled_at(day)` else `"provisional"` (FR-021, FR-022: decided at lookup time only) |
| `default_delay(has_key)` | 0.7 s with a key, 6.0 s without (research R1) |
| `usd_value(amount_piconero, usd_price)` | Exact product, scaled by 10⁻¹² (research R4) |
| `parse_import(text)` | Validates the whole file → `list[ImportRow]`, or an error naming the first bad line (FR-020) |
| `select_imports(rows, priced_days, cutoff)` | Keep rows with `date < cutoff` and no recorded price; count the rest as skipped (FR-019) |
| `summarize(...)` | Builds `PricingSummary`; `all_final` when no day with transactions lacks a final price (FR-014) |

`parse_history_price(body)` (primitives, pure) reads `market_data.current_price.usd` from the
Decimal-decoded body. It returns `None` when the data is missing and raises on a malformed,
zero, or negative value.

## Pricing step lifecycle

```text
needs = days with transactions and no final price        (one query)
requestable, too_old = plan_lookups(needs, today)
for day in requestable (oldest first):
    pace (sleep until min_request_delay since the previous request)
    lookup(day) ─▶ price            → upsert(status = price_status(day, now)); commit
                ├▶ no price / bad   → count no_price (or not_refreshed); next day
                ├▶ outside history  → count too_old; next day
                ├▶ 429              → sleep backoff, retry once; 429 again → stop(rate_limited)
                ├▶ other 401        → stop(key_rejected)
                ├▶ unreachable/5xx  → stop(unavailable)
                └▶ storage error    → RunError (FR-025)
on stop: the remaining requestable days are counted as no_price / not_refreshed
```
