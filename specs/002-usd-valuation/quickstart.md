# Quickstart: validating feature 002 (USD valuation)

A run and validation guide. Behavior details are in [contracts/](contracts/) and
[data-model.md](data-model.md). The gates are the same as in feature 001's quickstart.

## 1. Automated scenarios (via `run()` with fakes, a fake clock, and a recording `sleep`)

| Scenario | Expected |
|----------|----------|
| US1: 3 transaction days, source answers all | 3 prices; values exact, e.g. 1.234567890123 XMR × 152.3456 = 188.0809859615225088 |
| US1-7: transaction today | Provisional price |
| US1-8/9: provisional day, clock before / after settling | Refreshed and still provisional / refreshed and final |
| US1-4/6: all days final | 0 requests; `All transactions are valued.` |
| US2-1: source fails after 4 of 10 days | 4 kept; `6 days still have no price…`; exit 0 |
| US2-2: 429, then 429 on retry | `sleep(10)` recorded once; no further requests; warning; exit 0 |
| US2-3: Ctrl-C on the 3rd lookup | 2 prices kept; the next run requests only the rest |
| US2-4: pacing | Recorded `sleep` intervals ≥ 0.7 s (key) or 6.0 s (no key), or `min_request_delay` |
| US2-6: stop early | Every priced day is older than every unpriced day |
| US2-7: storage error while pricing | `RunError`, exit 1, earlier prices kept |
| US3: days older than 364 days | Never requested; counted in `too_old` |
| 401 with error_code 10012 / other 401 | Counted too old, then the next day / stop with a key-rejected warning |
| FR-006: final price, then a lookup with a different value | Unchanged (the trigger also rejects a direct UPDATE) |
| Migration 1 → 2 | Version-1 database with rows → version 2, rows intact, `daily_prices` empty |
| US4: CSV with 5 rows | 2 imported (final, source `import`), 3 skipped, recent days priced by the source |
| US4-4: bad row on line 4 | `Error: cannot import prices from …: line 4: …`, nothing imported, no lookups |
| SC-008: distinctive key | Appears in no stdout, stderr, or exception text |

## 2. Manual check against CoinGecko (makes real requests)

```sh
# a Demo key in ~/.config/monero-income/config.toml (chmod 600):
#   coingecko_api_key = "CG-…"
#   coingecko_api_key_type = "demo"     # or "pro" (pro-api host, x-cg-pro-api-key)
uv run monero-income --db-path /tmp/mi.db       # after feature 001's first sync
sqlite3 /tmp/mi.db "select * from daily_prices order by date_utc desc limit 3"
uv run monero-income --db-path /tmp/mi.db       # immediately again
```

| Check | Expected |
|-------|----------|
| First run | `Priced N days (1 provisional).` (today), nothing about rate limits, and at most about 4 min 20 s for 365 days with a key |
| Second run | Only today is looked up (refreshed, still provisional) |
| After 01:00 UTC the next day | Yesterday is refreshed and becomes `final` |
| Bad key | `Warning: … rejected the API key`, exit 0, key not shown |
| No key, many days | About 6 s between requests; slower than SC-012, which applies only with a key |
| Key without a type | `Error: invalid coingecko_api_key_type: required when coingecko_api_key is set`, exit 1 |
| SC-008 with `--coingecko-api-key` | The key appears in no output |

Delete `/tmp/mi.db` afterwards, and never commit it.
