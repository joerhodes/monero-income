# 21 - Implement Phase 3 for Spec 002

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-18

## Prompt
/speckit-implement Phse 3 (US1) only. Stop
after Phase 3 so I can review, run the gates, and commit.

## What Came Back
Phase 3 (US1, the MVP) is done: T015–T023 are marked [X] in tasks.md. I've stopped before Phase 4, and nothing is committed.

All five gates pass:

┌──────────────────────────────────┬──────────────────────────────────────────┐
│               Gate               │                  Result                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ ruff check / ruff format --check │ pass                                     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ mypy (strict)                    │ no issues in 57 files                    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ lint-imports                     │ 2 contracts kept                         │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ pytest                           │ 229 passed (up from 195), coverage 93.9% │
└──────────────────────────────────┴──────────────────────────────────────────┘

Built in this phase:
- price_source.py: the PriceSource protocol and the CoinGecko client:
  - one request per call, dates sent as dd-mm-yyyy, a 20-second timeout;
  - the header follows the key type (x-cg-demo-api-key or x-cg-pro-api-key), and no key header is sent without a key;
  - prices are decoded exactly as Decimal;
  - a 401 with error code 10012 means "outside history" and any other 401 means "key rejected", decided only after reading the body;
  - 429 means rate limited (with Retry-After when present), and anything else unusable means unavailable;
  - the key never appears in error text, even when a server echoes it back.
- pricing.py: price_days() looks up each day that needs a price, oldest first. It records each price with the right status (provisional or final) and commits it on its own. It also builds
  the PricingSummary.
- run.py: RunResult replaces SyncResult. After a successful sync, run() prices the days that need it and then closes the price source. The price source, clock and sleep defaults are filled in when run() is called.
- cli.py: adds --coingecko-api-key and --coingecko-api-key-type, and prints Priced N day(s) (M provisional). and All transactions are valued..
- tests/conftest.py: the new autouse fixture swaps in an empty fake price source and a no-op sleep, so no test can reach CoinGecko or wait in real time.
- Tests:
  - the client through a mock transport (22 tests);
  - US1 end to end: the exact value 188.0809859615225088, oldest-first order, today provisional, a refresh before settling, finalizing days later, no lookups after a failed sync, and final days never requested again;
  - CLI output, including the empty-database case.

Things to know:
- Two small additions not in the tasks: ImportSummary lives in orchestration/price_import.py now, as T020 asked; that module holds only that dataclass until US4. PricingSummary and RunResult fields have defaults, which keeps the CLI tests short.
- The type check for the fake price source, deferred from T014, is now in place.
- A fixture bug I hit and fixed. The package exports a run function with the same name as the run module, so the first version of the fixture patched the function instead of the module
  and every test errored. It now loads the module with importlib.import_module.
- Price-source failures aren't handled yet; that's Phase 4 (US2). If CoinGecko is unreachable or rate-limits the run, the error currently escapes run(), and the CLI shows Error: unexpected PriceUnavailableError: … with exit 1. US2 turns these into a warning, keeps every recorded price and exits 0. Until then, a real run against an unreachable price source fails after the sync. The sync results are still saved, because the sync commits before pricing starts.
- Uncovered lines in pricing.py (86%). The "no price" and "outside history" branches are exercised by the US2 and US3 tests.

## Notes
All gates run successfully.
All tasks for Phase 3 marked as done.
