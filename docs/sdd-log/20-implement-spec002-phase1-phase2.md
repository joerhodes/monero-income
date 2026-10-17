# 20 - Implement Phase1 and Phase2 for Spec 002

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-17

## Prompt
/speckit-implement Phase 1 (Setup) and Phase 2 (Foundational) only. Stop
after Phase 2 so I can review, run the gates, and commit.

## What Came Back
Phases 1 and 2 of feature 002 are done: T001–T014 are marked [X] in tasks.md. I've stoppedbefore Phase 3, and nothing is committed.

┌──────────────────────────────────┬──────────────────────────────────────────┐
│               Gate               │                  Result                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ ruff check / ruff format --check │ pass                                     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ mypy (strict)                    │ no issues in 52 files                    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ lint-imports                     │ 2 contracts kept                         │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ pytest                           │ 195 passed (up from 122), coverage 93.2% │
└──────────────────────────────────┴──────────────────────────────────────────┘

Built in this phase:
- Errors and models: the three price-source errors, the import-file error, and DailyPrice,
  PriceNeed and ImportRow.
- Schema version 2: the daily_prices table plus two triggers, one rejecting any change to a
  final price and one rejecting any delete. It's tested from an empty database and from a
  version-1 database with rows, and the rows survive. migrate() gained a to_version parameter
  so tests can build a version-1 database.
- Feature 001 tests (T006): the schema-version expectations in three files now say 2, and their
  "newer schema" cases use 3.
- prices_db.py: each looked-up price is saved and committed on its own, and the save never
  overwrites a final price. It also handles the list of days still needing a price, the import
  insert (one transaction, rolled back entirely on any conflict), and the "every day is final"
  check, which is False for an empty database. Prices are stored as plain decimal text and
  round-trip exactly.
- Settings: the new config keys and command-line options, with these rules:
  - the key type is required whenever a key is set;
  - the default host follows the key type, and an explicit URL wins;
  - min_request_delay must be a number from 0 to 60.

  The API key never appears in repr, warnings or errors.
- valuation.py (pure functions):
  - the 364-day cutoff;
  - the oldest-first lookup plan;
  - settling at 01:00 UTC the day after;
  - the default request intervals: 2.5 s with a key, 6.0 s without;
  - exact USD values. A test confirms the result stays exact where Python's default 28-digit precision would have rounded it.
- price_parse.py: the answer types and the parser for a price response.
- Test fakes: FakePriceSource, FakeClock and RecordingSleep.

Places where I didn't follow the tasks exactly:
- The type check for the fake price source (T014) moves to T018. The PriceSource Protocol it checks against doesn't exist until T018 creates it. A comment in the fake marks where the check goes.
- For T007/T008 (storage), I wrote the tests and the module together rather than confirming the tests failed first, as also happened in feature 001's database phase. The other Phase 2 test files were run and failed before their code existed.
- Two test mistakes in my own code, both fixed. I first typed the expected value of the high-precision valuation test by hand and got it wrong; it now comes from a 100-digit
  computation. I also removed an assertion that compared two values both rounded in the default
  context, which proved nothing.

Note for review: the new price errors in errors.py show as uncovered (76% on that file). Nothing raises them until the CoinGecko client in Phase 3 (T018). Overall coverage is still above the 90% floor.

## Notes
All gates pass for a manual run.
