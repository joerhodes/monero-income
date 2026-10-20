# 23 - Implement Phase 5 for Spec 002

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-19

## Prompt
/speckit-implement Phase 5 (US3) only. Stop
after Phase 5 so I can review, run the gates, and commit.

## What Came Back
Phase 5 (US3) is done: T028–T031 are marked [X] in tasks.md. I've stopped before Phase 6, and nothing is committed.

All five gates pass:

┌──────────────────────────────────┬──────────────────────────────────────────┐
│               Gate               │                  Result                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ ruff check / ruff format --check │ pass                                     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ mypy (strict)                    │ no issues in 59 files                    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ lint-imports                     │ 2 contracts kept                         │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ pytest                           │ 255 passed (up from 249), coverage 94.8% │
└──────────────────────────────────┴──────────────────────────────────────────┘

T030 needed no code change. The four new integration tests in test_pricing_history.py passed as soon as they were written. US1 and US2 had already built what this story needs:
- the 364-day cutoff in plan_lookups;
- counting too-old days in the summary;
- treating an "outside history" answer as "count it and go on to the next day."

So for this story the tests confirm existing behavior rather than drive new code. They cover:
- The window edge: a day 365 days old is never requested and is counted too old; a day 364 days old is requested (SC-006).
- A provisional day that aged out: if the tool isn't run for a year, the day isn't requested, stays provisional, and is counted too old rather than as a failed refresh.
- An "outside history" answer: the day is counted too old, the next day is still requested, and pricing doesn't stop.
- Separate counts: too-old, no-price and not-refreshed days are each counted on their own (US3-2).

T031 added the CLI line, which was the only change needed:
- 2 days are older than the price history and can't be looked up; use --import-prices to add them.
- 1 day is older than the price history and can't be looked up; use --import-prices to add it. (singular)

It prints after the no-price and not-refreshed lines.

The line points to --import-prices, which doesn't exist until Phase 6 (US4). If you run the tool between committing this phase and finishing US4, following that hint gives a usage error. It's harmless if US4 comes next, but don't release between the two.

## Notes
All gates pass a manual run.
Code passes a quick visual inspection.
