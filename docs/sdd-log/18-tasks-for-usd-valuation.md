# 18 - Tasks for USD Valuation

**Command:** /speckit-tasks
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-17

## Prompt
/speckit-tasks

## What Came Back
I wrote specs/002-usd-valuation/tasks.md with 43 tasks. All of them match the required checklist format, and 20 can run in parallel.

┌──────────────┬────────────┬─────────────────────────────────────────────────────────────┐
│    Phase     │   Tasks    │                      What it delivers                       │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 1 Setup      │ T001       │ Confirms all five gates pass on the branch before any       │
│              │            │ change                                                      │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 2            │ T002–T014  │ Price errors and types, schema v2 (daily_prices table and   │
│ Foundational │ (13)       │ the immutability triggers), price storage, new settings,    │
│              │            │ pure valuation rules, price-response parsing, test fakes    │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 3 US1 (P1)   │ T015–T023  │ CoinGecko client, pricing loop (oldest first, provisional   │
│ MVP          │ (9)        │ vs final), RunResult, CLI lines                             │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 4 US2 (P2)   │ T024–T027  │ Pacing (0.7 s with a key, 6.0 s without), one retry on a    │
│              │ (4)        │ rate limit, stop rules, failed run on storage errors        │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 5 US3 (P2)   │ T028–T031  │ The 364-day cutoff, the "outside history" answer, the       │
│              │ (4)        │ too-old count and line                                      │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 6 US4 (P3)   │ T032–T038  │ CSV import: whole-file validation, selection,               │
│              │ (7)        │ one-transaction insert, --import-prices                     │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 7 Polish     │ T039–T043  │ Wording scan, a key-secrecy test across every outcome,      │
│              │ (5)        │ README, all gates, manual check against CoinGecko           │
└──────────────┴────────────┴─────────────────────────────────────────────────────────────┘

How each story is tested on its own:
- US1: three days are priced, values are exact (1.234567890123 XMR × 152.3456 = 188.0809859615225088), today is provisional, and a refresh after settling makes a price final. Final days are never requested again.
- US2: with ten days to price and a source that fails on the fifth, four prices are kept, six are reported as missing, and the run exits 0. Pacing intervals, the single retry and storage-error failures are checked through the recorded sleeps.
- US3: a day exactly 365 days old is never requested, and a 364-day-old day is. Both appear in
  the right counts.
- US4: a five-row CSV gives 2 imported and 3 skipped, and a bad row rejects the whole file before any lookups.

Feature 001 code and tests this changes:
- Schema version 1 → 2: the version checks in three 001 test files are updated (T006).
- SyncResult becomes RunResult: the 001 CLI and its tests are updated (T017, T021).
- New autouse fixture (T023): every run now prices after syncing. Without the fixture, the 001 integration tests would try to reach CoinGecko and sleep for real between requests. It replaces the real price source with an empty fake and the real sleep with a no-op.

That fixture needs one small change to the run-api contract, recorded in the Notes at the end of tasks.md. The price source, clock and sleep parameters of run() default to None and are filled in when run() is called, the same approach 001 used for HOME.

Suggested MVP: Phases 1–3 (T001–T023), then the "First run" manual check in quickstart §2, using a Demo key.
