# 22 - Implement Phase 4 for Spec 002

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-18

## Prompt
/speckit-implement Phase 4 (US2) only. Stop
after Phase 4 so I can review, run the gates, and commit.

## What Came Back
Phase 4 (US2) is done: T024–T027 are marked [X] in tasks.md. I've stopped before Phase 5, and nothing is committed.

All five gates pass:

┌──────────────────────────────────┬──────────────────────────────────────────┐
│               Gate               │                  Result                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ ruff check / ruff format --check │ pass                                     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ mypy (strict)                    │ no issues in 58 files                    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ lint-imports                     │ 2 contracts kept                         │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ pytest                           │ 249 passed (up from 229), coverage 94.0% │
└──────────────────────────────────┴──────────────────────────────────────────┘

price_days() in pricing.py now:
- Paces requests: each request starts at least the configured interval after the previous one (2.5 s with a key, 6.0 s without, or min_request_delay). There's no wait before the first request.
- Retries a rate limit once: it waits 10 seconds, or Retry-After capped at 60, then tries the same day again.
- Stops cleanly: a second rate limit, a rejected key or an unreachable source ends pricing for the run without raising. The days not reached are counted as having no price, or as provisional prices that couldn't be refreshed. The reason for stopping is recorded in StopReason.
- Lets serious errors through: storage errors and Ctrl-C still propagate. A storage error becomes Error: cannot write to database … with exit 1, and every price recorded before it is kept.

The Phase 3 gap is closed: an unreachable or rate-limiting CoinGecko no longer fails the run.

CLI:
- New lines N days still have no price; a later run will try again. and N provisional prices couldn't be refreshed; a later run will try again., with singular forms ("1 day still has…").
- When pricing stopped early, stderr gets Warning: price lookups stopped: <reason> and the exit status is still 0.

Tests (test_pricing_failures.py, 13 cases, plus CLI cases):
- a source failing on day 5 of 10 keeps 4 prices, reports 6 with no price, and the next run requests only the other 6;
- a rate limit followed by a price succeeds on the retry; two rate limits in a row stop pricing with no further requests;
- Retry-After is honoured, capped at 60 seconds;
- Ctrl-C keeps the prices already recorded;
- pacing with a key, without a key, and with min_request_delay;
- an unreachable source and a rejected key both stop pricing cleanly;
- a storage error fails the run and keeps earlier prices;
- a failed refresh keeps the provisional price;
- after both the outage and the Ctrl-C cases, the stored prices match one uninterrupted run (the G2 check from the analysis).

Things to know:
- Test fake extension: FakePriceSource now accepts a list of answers per day, used up one per call, to script "rate limited, then a price."
- Where the stop warning comes from: the CLI prints it through its own reporter, as T027 described. The run-api contract says run() sends it to reporter.warning. The output is identical; if you'd rather run() emit it, it's a small move, and CLI tests would then need their fake run to call the reporter.
- Retry-After: 0 is treated like a missing value, so the run waits 10 seconds rather than retrying immediately. That's the conservative choice; say if you want 0 honoured.
- Uncovered lines in pricing.py (91%). The "outside history" and per-day "no price" branches are US3's, and the defensive fallback in _stop_reason can't happen with the current error types.

## Notes
