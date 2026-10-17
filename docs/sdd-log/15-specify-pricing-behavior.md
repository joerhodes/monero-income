# 15 - Specify Pricing Behavior

**Command:** /speckit-specify
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-17

## Planning Notes - Parking here until spec is complete
1. Before requesting: skip any day older than the cutoff (default 365 days, configurable).
2. On a 401: read the body first.
   - error_code 10012 → the day is outside the price history; record it as such and continue with other days.
   - any other 401 → a real authentication problem (bad or missing key); report it as such.
4. On a 429: rate limited; stop pricing for this run, keep what's recorded, and let the next run continue.

## Prompt
/speckit-specify monero-income records a Monero wallet's incoming
transactions locally (feature 001). This feature values each recorded
transaction in USD. CSV output and on-screen summaries are separate,
later features and are out of scope.

Behaviors:
- Every run, after a successful sync, looks up the USD price for each
  UTC calendar day that has recorded transactions but no price yet.
- Each transaction is valued at the USD price for its UTC calendar day;
  all transactions on the same day share that day's price.
- Prices and USD values are kept at full precision; rounding happens
  only on output.
- Once a day's price is recorded, it is not changed.
- If the lookup is interrupted, prices already recorded are kept, and
  the next run looks up the rest.
- If the price source is unavailable or rate-limits the run, prices
  already recorded are kept, the run reports how many days still lack a
  price, and the next run continues. The run does not fail.
- The tool paces its requests to stay within the price source's limits.
- The price source only provides history for a limited recent period. A
  day older than that period is not requested; its transactions remain
  unvalued, and the run reports such days separately from temporary
  failures.
- The user may supply an API key for the price source. It is never
  shown in any output.

P3 (optional): the user can import daily USD prices from a previous
xmr-income-report database. Imported prices fill in days that have no
price yet and never replace a recorded price.

## What Came Back
The spec is written at specs/002-usd-valuation/spec.md, on the new branch 002-usd-valuation. It
passes 15 of the 16 checklist items. The one failing item is a single [NEEDS CLARIFICATION]    marker that needs your answer before the spec is complete. I'll finish validation and the remaining hooks after you reply.Question 1: Pricing the current UTC dayContext: from Edge Cases: "Current UTC day (not yet over): Should the tool record a price forthe current, incomplete UTC day?"
What we need to know: Your description says "Once a day's price is recorded, it is not changed." Today's price isn't final until the UTC day ends, though. Two other documents bear onthis:                                                                                          - Constitution Principle VI says provisional prices "MAY be refreshed until they are           finalized."
- The README lists "price finalization for recent days" as a roadmap goal of this rewrite.

Suggested Answers:

Option: A
Answer: Wait until the day has ended; never price the current UTC day
Implications: Every recorded price is final and "never changed" holds without exception. Today's
transactions stay unvalued until the next run after midnight UTC.
────────────────────────────────────────
Option: B
Answer: Record a provisional price for the current day, refresh it on each run, and finalize it
once the day has ended
Implications: Today's transactions get a USD value right away. Uses the constitution's
provisional/finalized distinction, so "not changed" applies only to finalized prices. It adds
a price status, and is likely the "price finalization" goal in the README.
────────────────────────────────────────
Option: C
Answer: Treat the most recent N days as provisional (for example, refreshed until 2 days after
they end), then finalize
Implications: Covers sources that revise recent daily prices after the fact. Most complex; only
worth it if the source is known to revise recent days.
────────────────────────────────────────
Option: Custom
Answer: Provide your own answer
Implications: Describe the rule, for example how long a day stays provisional.

Your choice: Reply with A, B, C, or a custom answer.

## Answer
C with the understanding that the tool does not run every day

## What Came Back
I added your answer (Option C) to the spec, and it now passes all 16 checklist items with no 
open clarification markers.                                                                  

- Branch: 002-usd-valuation
- Feature directory: specs/002-usd-valuation/
- Spec: specs/002-usd-valuation/spec.md
- Checklist: specs/002-usd-valuation/checklists/requirements.md

How I wrote your answer into the spec:
- Settled days: a day is "settled" once a settling period has passed since it ended. A price 
  looked up before then is recorded as provisional; a price looked up afterwards is final (FR-021).
- Your point about not running daily: a provisional price becomes final only through a lookupmade after the 
  day has settled, never just because time has passed (FR-022, SC-009). If you skip a week, the next run 
  looks those days up once more and finalizes them.
- Failed refresh: if a refresh lookup fails, the provisional price is kept and the day's transactions 
  stay valued at it (FR-023).
- Final means fixed: the "never changed" rule now applies to final prices only (FR-006, FR-007, SC-003).
  That matches constitution Principle VI.
- What the run reports: how many days it priced, how many of those are provisional (FR-013), and how many
  days still lack a price.
- New edge cases:
  - Today is priced provisionally.
  - A day first priced after it settled is recorded as final straight away.
  - If the tool goes unused longer than the source's history period, a provisional day can't be refreshed. It stays
    provisional and is counted with the days too old to price.
- Imports: an imported price is final for a settled day and provisional otherwise. Imports never replace an existing price.

Defaults to check during /speckit-clarify or planning:
- Settling period: 2 days, from your example. Planning can lengthen it if the chosen price source revises recent days for longer.
- Daily price definition: the same one the original xmr-income-report tool used, so reports match the reference implementation. I couldn't confirm what that definition is: the legacy-code analysis is in docs/sdd-log/, which I'm not allowed to read.
- A rejected API key is treated as a temporary failure: the run reports it without showing the key and still ends successfully.
- The price source itself, its rate limits and its history period (for example, 365 days without a paid plan) are left for planning.

I also corrected acceptance scenario US1-3 before you answered. I had written the example USD value by hand and got it wrong; it's now 188.0809859615225088, which I checked with exact decimal arithmetic.

## Notes
I had forgotten about the legacy code analysis and the agent caught it.

## Prompt
Update specs/002-usd-valuation/spec.md with these decisions. Keep
requirements, edge cases, and success criteria consistent. Add a
Clarifications entry for them. Change nothing else.

1. Daily price definition: a day's price is the price source's daily
   price for that UTC calendar date. Replace the assumption that refers
   to the original tool's definition, which can't be verified here.
2. Settling period: the source documents that a completed UTC day's data
   is published about 35 minutes after midnight UTC. Set the settling
   period to 1 hour after the end of the UTC day; planning may confirm.
3. Rate limits: after a brief retry, stop looking up prices for the rest
   of the run (as FR-009 says). Do not keep requesting later days.
4. Lookup order: days are looked up oldest first, so days nearest the
   end of the history period are priced before they age out.
5. Errors that are not price-source failures (for example, storage
   errors) during pricing end the run with a message and a failure
   status, as in feature 001. Only price-source problems leave the run
   successful.

## What Came Back
I added all five decisions to specs/002-usd-valuation/spec.md, with matching Clarifications entries under Session 2026-10-17. Nothing else changed, and no references to a 2-day settling period or the original tool's price definition remain.

┌─────┬─────────────────────────────────────────┬──────────────────────────────────────────┐
│  #  │                Decision                 │             Where it landed              │
├─────┼─────────────────────────────────────────┼──────────────────────────────────────────┤
│ 1   │ A day's price is the source's daily     │ FR-003; replaces the assumption about    │
│     │ price for that UTC date                 │ the original tool's definition           │
├─────┼─────────────────────────────────────────┼──────────────────────────────────────────┤
│     │ Settling period of 1 hour after the UTC │                                          │
│ 2   │  day ends (data is published about 35   │ FR-021; Assumptions                      │
│     │ minutes after midnight); planning may   │                                          │
│     │ confirm                                 │                                          │
├─────┼─────────────────────────────────────────┼──────────────────────────────────────────┤
│     │ On a rate limit, one brief retry, then  │ FR-009; US2 scenario 2; new edge case;   │
│ 3   │ no more price requests that run         │ new SC-011 (0 requests after an          │
│     │                                         │ uncleared rate limit)                    │
├─────┼─────────────────────────────────────────┼──────────────────────────────────────────┤
│     │                                         │ New FR-024; new US2 scenario 6; new edge │
│ 4   │ Days are looked up oldest first         │  case; new SC-010 (every day priced is   │
│     │                                         │ older than every day left unpriced)      │
├─────┼─────────────────────────────────────────┼──────────────────────────────────────────┤
│     │ Errors other than price-source problems │ New FR-025; new US2 scenario 7; new edge │
│ 5   │  end the run with a message and a       │  case; the exit-status assumption now    │
│     │ failure status                          │ limits "run still succeeds" to           │
│     │                                         │ price-source problems                    │
└─────┴─────────────────────────────────────────┴──────────────────────────────────────────┘

Two notes:
- Rate-limit retry: I applied the brief retry only to rate limits, as you described. An unavailable source or a rejected key still stops pricing straight away (FR-009). Say if you want the retry to cover those too.
- Storage errors during pricing: the edge case for a second run started during another already said the second run "may fail with a storage error." Under FR-025 that is now explicitly a failed run, so the two are consistent.

The next step is /speckit-clarify, then /speckit-plan.
