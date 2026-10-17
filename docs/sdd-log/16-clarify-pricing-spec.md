# 16 - Clarify Pricing Spec

**Command:** /speckit-clarify
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-17

## Prompt
/speckit-clarify

## What Came Back
Two issues have the most effect on scope and tests: how the import (US4) is started, and how failed refreshes of provisional prices are counted. Here's the first.

Question: How should the user start the optional price import from an xmr-income-report database? (FR-019)

Why it matters: Feature 001 made the tool a single command with no subcommands, so this decides whether the CLI changes shape. It also decides whether an import run also syncs and looks up prices.

Recommended: Option A. It keeps 001's single-command design. Running the import before the price lookups means the source is never asked about days the import can fill, which matters most for old days beyond the source's history.

┌────────┬──────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                   Description                                    │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ A      │ An option on the normal run (for example --import-prices PATH). The run syncs,   │
│        │ imports prices from the file, then looks up whatever is still missing            │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ B      │ A separate command (for example monero-income import-prices PATH) that only      │
│        │ imports, with no sync and no lookups. Adds subcommands to the CLI                │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ C      │ Leave the import out of this feature and specify it later                        │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                                     │
└────────┴──────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
A

## What Came Back
Recorded: the import is an option on the normal run (for example --import-prices PATH). The run syncs, imports, then looks up only what's still missing. I updated US4 and FR-019, and added  two scenarios: imported days aren't requested, and a failed sync means no import. An unreadab import file now fails the run before any lookups (FR-020, consistent with FR-025).

---

Question: When this run couldn't refresh a day that already has a provisional price, how should that day show up in the run's report? (FR-009, FR-013)

Why it matters: FR-009 says the run reports "how many days still lack a price," but a day with an unrefreshed provisional price does have a price and its transactions are valued. Tests need to know which count it belongs in.

Recommended: Option A. Days with no price have unvalued transactions; days with a stale provisional price have valued but not-yet-final ones. Keeping the counts separate tells the user exactly what a later run will fix, without overstating what's missing.

┌────────┬──────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                   Description                                    │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ A      │ A separate count, for example "2 days still have no price; 1 provisional price   │
│        │ couldn't be refreshed"                                                           │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ B      │ Include them in "days still lacking a price" (meaning lacking a final price), as │
│        │  one count                                                                       │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ C      │ Don't report them; the day already has a price                                   │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                                     │
└────────┴──────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer 
A

## What Came Back
Recorded: provisional prices that couldn't be refreshed get their own count, separate from days with no price and from days too old to price (FR-009, FR-012, and the refresh-failure edge case).

---

Question: How long may a first run take when it has to price a full year of days?

Why it matters: With pacing, looking up 365 days one at a time could take from about 10 minutes to over an hour, depending on the source's limits. A time limit would push planning toward a source or method that returns many days per request, which changes the design.

Recommended: Option B. A first run of under 5 minutes keeps the tool pleasant to set up, and it's achievable with sources that return a range of daily prices in one request. Later runs only price a few days, so they're quick either way.

┌────────┬──────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                   Description                                    │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ A      │ No limit: pacing decides; a long first run is acceptable because it happens once │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ B      │ Under 5 minutes for a full year of days                                          │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ C      │ Under 30 minutes for a full year of days                                         │
├────────┼──────────────────────────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                                     │
└────────┴──────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
B

## What Came Back
I asked three of the five allowed questions and stopped there, since what remains is low-impact or a planning decision. All three answers are recorded in specs/002-usd-valuation/spec.md. Each has a Q&A entry in the 2026-10-17 Clarifications session and is reflected in the related sections.                                                                                     

Question: How is the price import started?
Your answer: A: an option on the normal run (for example --import-prices PATH); the run syncs,
imports, then looks up only what's missing
What changed in the spec: US4 text plus two new scenarios (imported days aren't requested; a
failed sync means no import); FR-019; FR-020 now says an unreadable import file fails the run
before any lookups
────────────────────────────────────────
Question: How do unrefreshed provisional prices show up in the report?
Your answer: A: their own count, separate from days with no price
What changed in the spec: FR-009, FR-012, and the refresh-failure edge case
────────────────────────────────────────
Question: How long may a first run take to price a full year?
Your answer: B: under 5 minutes
What changed in the spec: New SC-012 (the pricing step finishes in under 5 minutes with 0
rate-limit refusals); the price-source assumption now requires planning to pick a lookup
method that meets it

Spec quality checklist: still 16 of 16 passing, with no items changed.

Coverage

┌───────────────────────────────────────────────────┬──────────────────────────────────────┐
│                     Category                      │                Status                │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Scope and behavior                                │ Resolved (how the import is started) │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Data model, lifecycle                             │ Clear (provisional and final prices, │
│                                                   │  settling, oldest first)             │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Messages, errors, empty states                    │ Resolved (the separate counts)       │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Performance                                       │ Resolved (SC-012)                    │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Reliability and failure handling                  │ Clear (FR-009, FR-023, FR-025)       │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Security and privacy                              │ Clear (FR-015, SC-008)               │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ External price source, its limits and history     │ Deferred to planning                 │
│ period                                            │                                      │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Format of the previous xmr-income-report database │ Deferred to planning                 │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Exact message wording                             │ Deferred to planning (contracts)     │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Whether a "no price for this day" answer stops    │ Outstanding, low impact (the edge    │
│ pricing or moves on to the next day               │ case implies it moves on)            │
├───────────────────────────────────────────────────┼──────────────────────────────────────┤
│ Terminology                                       │ Clear                                │
└───────────────────────────────────────────────────┴──────────────────────────────────────┘

Check during planning: SC-012 combined with SC-007 means a full year of prices can't be fetched one day at a time with slow pacing. The source and lookup method planning picks need to meet both.

## Prompt for pricing import
Update specs/002-usd-valuation/spec.md, User Story 4 and FR-019/FR-020:
- Import reads a CSV file with a header row and two columns, date_utc
  (YYYY-MM-DD) and usd_price (USD per 1 XMR), not a previous database.
- Imported prices are recorded only for days older than the price
  source's history period that have no recorded price; days inside the
  period are always priced by the source. Imported prices are final.
- A file with any invalid row (bad date, missing or non-positive price,
  duplicate date) is rejected as a whole: nothing is recorded, and the
  error names the first bad row.
- Rows for days that already have a price, or that are inside the
  history period, are skipped and counted in the run's report.
- The import is requested with an option on the main command; the run
  then continues as normal.
Add a Clarifications entry. Change nothing else.

## What Came Back
I updated User Story 4, FR-019 and FR-020 for the CSV import, and added a Clarifications entry. Nothing else in the spec changed.

- User Story 4 is now "Import prices from a CSV file":
  - Independent test: five rows. Two old, unpriced days get imported final prices. Three rows 
    (an already-priced day and two recent days) are skipped and counted. The recent days are  
    priced by the source.                                                                     
  - Scenarios:                                                                                
    i. Old, unpriced days are imported as final.                                              
    ii. A day that already has a price is skipped and counted, and the price is unchanged.    
    iii. A day inside the history period is skipped and counted, then priced by the source.
    iv. Any invalid row rejects the whole file. The error names the first bad row, and the run fails before any lookups.
    v. Importing the same file again records nothing.
    vi. A failed sync means no import.
- FR-019:
  - The option goes on the main command.
  - The file has a header row with date_utc (YYYY-MM-DD) and usd_price (USD per 1 XMR).
  - The import runs after a successful sync and before lookups, then the run continues as normal.
  - Prices are recorded, as final, only for days older than the history period that have no price.
  - Every other row is skipped and never replaces a price. The run reports how many prices it imported and how many rows it skipped.
- FR-020: a file with an invalid row is rejected as a whole. That covers a bad date, a missing or non-positive price, or a repeated date. I also counted a missing or wrong header, or an unreadable file, as rejections. The error names the first bad row (or the header or file problem), nothing is recorded, and the run fails before any lookups.

Two choices I made that you didn't specify:
- Rejecting a missing header or an unreadable file. Your list covered invalid rows only; these seemed to fall under the same rule.
- A single "skipped" count. Already-priced days and recent days are counted together, not separately. Say if you want them reported separately.

One stale line I didn't touch: the Assumptions section still says "The previous xmr-income-report database format is the one the original tool writes…" That no longer fits the CSV import. It could be replaced with a CSV assumption or deleted; I left it because you asked me not to change anything else. The earlier Clarifications entry about the import option still names "an xmr-income-report database." I left it as history; the new entry says it supersedes that wording.


## Notes
I manually removed the stale assumption.
