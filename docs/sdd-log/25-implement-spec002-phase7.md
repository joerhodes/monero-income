# 25 - Implement Phase 7 for Spec 002

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-19

## Prompt
/speckit-implement Phase 7 (Polish) only. Stop
after Phase 7 so I can review, run the gates, and commit.

## What Came Back
Phase 7 is done except T043, the manual check against CoinGecko, which needs you to run it. T039–T042 are marked [X] in tasks.md; T043 is the only unchecked task in feature 002. Nothing is committed.

All five gates pass:

┌──────────────────────────────────┬──────────────────────────────────────────┐
│               Gate               │                  Result                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ ruff check / ruff format --check │ pass                                     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ mypy (strict)                    │ no issues in 63 files                    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ lint-imports                     │ 2 contracts kept                         │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ pytest                           │ 300 passed (up from 286), coverage 95.7% │
└──────────────────────────────────┴──────────────────────────────────────────┘

- T039: the "transfer" wording test already scanned every orchestration module. It now also asserts that pricing.py, price_import.py and valuation.py are scanned, so a rename can't drop them silently.
- T040: the new tests/integration/test_key_secrecy.py (14 cases) drives the real CLI and the real run(). Only the wallet, the price source, the clock and sleep are faked.
  - Where the key comes from: the config file, or --coingecko-api-key.
  - Outcomes covered: success, rate-limited twice, key rejected, source unavailable, and a storage error.
  - Invalid config cases: a key with no type, an unknown type, and a coingecko_url with the key embedded as a password.
  - What it checks: the key never appears in stdout, stderr, warnings, or the result's repr, and there's never a traceback.
- T041: the README's Usage section now covers:
  - the new config keys, with coingecko_api_key_type (demo or pro), and why the config file is better than --coingecko-api-key;
  - the pacing defaults (2.5 s with a key, 6 s without) and min_request_delay;
  - the new command options and all the pricing output lines;
  - provisional and final prices;
  - the price source failing: the run warns and still succeeds;
  - the 364-day history limit, and --import-prices with an example CSV.

  Intro and Status are unchanged, so Status still says "Not yet usable." Edit that line when
  you're ready to release.
- T042: all five gates pass, as in the table above.

To finish T043, run the checks in specs/002-usd-valuation/quickstart.md §2 against the real CoinGecko API:
- With a Demo key: a first run, then an immediate second run.
- After 01:00 UTC the next day: confirm yesterday's price becomes final.
- A bad key: expect a warning, exit 0, and the key not shown.
- Without a key: requests about 6 seconds apart.
- A key with no type set: expect Error: invalid coingecko_api_key_type ….

Record the results in the PR description, mark T043 [X], and don't commit /tmp/mi.db.

## Notes
All gates pass a manual run.
All code passes a quick visual inspection.
User tests:
  - `--help` displays new options
  - First run updates `user_version` to 2, (sqlite migrations).
  - First run syncs `transactions` from 672 to expected 680.
  - First run adds expected 230 `daily_prices`.
    - One date to old to price, 2025-08-29.
    - Two prices marked provisional, 2026-10-18 and 2026-10-19.
  - Next run adds 0 `daily_prices`.
  - Removing SQLite file and running:
    - Creates new file
    - Adds 680 `transactions`
    - Add 230 `daily_prices`
  - Using import with full pricing export
    - Syncs 680 `transactions`
    - Imports 231 `daily_prices` as final, (two provisional)
    - Adds 0 new `daily_prices`
