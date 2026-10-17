# 19 - Analysis for Spec 002 USD Valuation

**Command:** /speckit-analyze
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-17

## Prompt
/speckit-analyze

## What Came Back
Specification Analysis Report: feature 002 (USD valuation)

There are no CRITICAL or HIGH findings, and no constitution conflicts. All 37 requirements have at least one task. I found two MEDIUM gaps, both missing automated checks, and five LOW items. I didn't change any files.

ID: G1
Category: Coverage gap
Severity: MEDIUM
Location(s): spec SC-012; tasks T011, T024, T043
Summary: No automated test checks "365 days in under 5 minutes with a key." T011 only checks the
0.7 s default; the real check is the manual run in T043.
Recommendation: Add a case to T024: 365 requestable days with a key, a fake price source that
answers instantly, and a recorded sleep. Assert the total sleep is under 300 s and that no 429
 occurs.
────────────────────────────────────────
ID: G2
Category: Coverage gap
Severity: MEDIUM
Location(s): spec SC-005; tasks T024 (US2-1, US2-3)
Summary: After an interruption or failure, T024 checks only which days are requested next. It
doesn't assert that the final prices match one uninterrupted run, which feature 001 did for
sync.
Recommendation: Extend T024: after the follow-up run, compare daily_prices (date, price, status)
with a fresh uninterrupted run on the same fake data.
────────────────────────────────────────
ID: G3
Category: Coverage gap
Severity: LOW
Location(s): spec Edge Cases ("Second run started while one is pricing"); tasks
Summary: No test covers two runs pricing at once. The storage-error path is covered generically
by US2-7.
Recommendation: Optional: hold a write lock (as feature 001's concurrency test did) during
upsert_price, and expect RunError with nothing lost.
────────────────────────────────────────
ID: I1
Category: Inconsistency
Severity: LOW
Location(s): contracts/run-api.md; tasks Notes and T020
Summary: The contract still shows value defaults for price_source_factory, clock and sleep. T020
makes them None, resolved at call time; only the Notes record this.
Recommendation: Update run-api.md to match T020.
────────────────────────────────────────
ID: I2
Category: Inconsistency
Severity: LOW
Location(s): data-model.md (Settings); tasks T010
Summary: T010 adds import_prices: Path | None to Settings, but the data model lists it only on
CliOptions.
Recommendation: Add it to the data model's Settings list, or keep it on CliOptions and pass it
separately.
────────────────────────────────────────
ID: U1
Category: Underspecification
Severity: LOW
Location(s): tasks T020
Summary: "Define ImportSummary here or in price_import.py" leaves the module undecided, though
T032–T038 need it.
Recommendation: Pick orchestration/price_import.py and re-export it from run.py.
────────────────────────────────────────
ID: U2
Category: Underspecification
Severity: LOW
Location(s): spec FR-014; contracts/cli.md; tasks T019, T022
Summary: With no recorded transactions, all_days_final is vacuously true, so the run would print
"All transactions are valued." on an empty database.
Recommendation: Print that line only when at least one transaction is recorded; state it in
contracts/cli.md and test it in T017.

Coverage Summary

┌─────────────────────────────┬────────────┬─────────────────┬────────────────────────────┐
│         Requirement         │ Has Task?  │    Task IDs     │           Notes            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-001 price days without a │ ✅         │ T008, T016,     │                            │
│  final price                │            │ T019            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-002 no pricing after a   │ ✅         │ T016, T020      │                            │
│ failed sync                 │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-003 daily price per UTC  │ ✅         │ T015, T018      │                            │
│ date                        │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-004 exact USD value      │ ✅         │ T011, T016      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-005 full precision       │ ✅         │ T007, T012,     │                            │
│                             │            │ T015            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-006 final price          │ ✅         │ T004, T005,     │ Also enforced by trigger   │
│ immutable                   │            │ T007            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-007 final days not       │ ✅         │ T016            │                            │
│ re-requested                │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-008 interruption keeps   │ ✅         │ T024            │ See G2                     │
│ prices                      │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-009 stop on source       │ ✅         │ T024, T026,     │                            │
│ problems                    │            │ T027            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-010 pacing               │ ✅         │ T024, T026      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-011 skip old days        │ ✅         │ T011, T028      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-012 separate counts      │ ✅         │ T028, T029      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-013 priced and           │ ✅         │ T017, T022      │                            │
│ provisional counts          │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-014 all valued           │ ✅         │ T016, T017      │ See U2                     │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-015 API key handling     │ ✅         │ T009, T015,     │                            │
│                             │            │ T017, T040      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-016 reject bad prices    │ ✅         │ T012            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-017 prices persist       │ ✅         │ T007, T008      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-018 "transactions"       │ ✅         │ T039            │                            │
│ wording                     │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-019 CSV import           │ ✅         │ T032–T038       │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-020 invalid import file  │ ✅         │ T032, T033      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-021 settling             │ ✅         │ T011, T016      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-022 finalize only by     │ ✅         │ T016            │                            │
│ lookup                      │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-023 failed refresh keeps │ ✅         │ T024            │                            │
│  price                      │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-024 oldest first         │ ✅         │ T011, T016      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ FR-025 storage error fails  │ ✅         │ T024            │                            │
│ run                         │            │                 │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-001                      │ ✅         │ T016            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-002                      │ ✅         │ T011            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-003                      │ ✅         │ T004, T007      │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-004                      │ ✅         │ T024            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-005                      │ ⚠️ partial │ T024            │ See G2                     │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-006                      │ ✅         │ T028            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-007                      │ ✅ (by     │ T024            │ Pacing intervals; a real   │
│                             │ proxy)     │                 │ check is in T043           │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-008                      │ ✅         │ T040            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-009                      │ ✅         │ T016            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-010                      │ ✅         │ T024            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-011                      │ ✅         │ T024            │                            │
├─────────────────────────────┼────────────┼─────────────────┼────────────────────────────┤
│ SC-012                      │ ⚠️ manual  │ T011, T043      │ See G1                     │
│                             │ only       │                 │                            │
└─────────────────────────────┴────────────┴─────────────────┴────────────────────────────┘

Constitution alignment: no issues.
- Principle I: the new modules follow the existing layers, the CLI only imports orchestration, and the fakes use the primitives' types.
- Principle III: decoding uses parse_float=Decimal, and valuation runs under a context that raises on any rounding.
- Principle IV: the client makes one request per call; parsing, the cutoff, settling and import validation are pure functions.
- Principle V: the price source is behind a Protocol, and the clock and sleep are injected, with an autouse fixture.
- Principle VI: final prices are protected by both the conditional insert and the database triggers, and migration 1 → 2 is tested from a version-1 database.
- Principle VII: all five gates run in T042.

Unmapped tasks: none. T001 is the baseline check, T006, T021 and T023 keep feature 001's tests working, and T041 is the README.

Metrics:
- Requirements: 37 (25 FR, 12 SC)
- Tasks: 43
- Coverage: 100% have at least one task (2 partial: SC-005, SC-012)
- Ambiguities: 0
- Duplications: 0
- Critical issues: 0
Next Actions

There's nothing blocking, so you could run /speckit-implement now. Before that, the two MEDIUM gaps are small additions to T024:
- G1: check the 365-day sleep budget with a key.
- G2: compare prices after an interruption against an uninterrupted run.

The LOW items (I1, I2, U1, U2, G3) are a few lines in tasks.md, contracts/run-api.md, contracts/cli.md and data-model.md, or can be settled during implementation.

Would you like me to suggest concrete remediation edits for the top 4 issues (G1, G2, U2, I1)?

## Follow Up Prompt
Update specs/002-usd-valuation/spec.md:
- Remove SC-012. A first run's duration is not a requirement for this
  personal tool.
- Replace SC-007 with: the default request pacing stays within the price
  source's published limits for unauthenticated and demo-key use; when a
  rate-limit refusal does occur, no recorded price is lost and a later
  run prices the remaining days (as FR-009 and SC-004 already require).
Add a Clarifications entry. Change nothing else.

Then update the plan and tasks to match: set the default request
interval conservatively for the demo tier (about 2.5 seconds), keep it
configurable via min_request_delay, and record the reasoning in
research.md. Update T011's default-interval test, remove the SC-012
timing case from T024 and T043, and resolve G1 as no longer applicable.

For G2, extend T024: after the follow-up run, compare daily_prices
(date, price, status) with a fresh uninterrupted run on the same fake
data, with both runs using the same fixed clock.

For G3, add no new test: concurrent runs use the same storage layer and
locking as feature 001, whose lock test already covers it, and the
storage-error path is covered by US2-7. Record G3 as accepted in the
analysis notes.

I1: update contracts/run-api.md to match T020 (None defaults, resolved at
call time).
I2: add import_prices: Path | None to the Settings entity in
data-model.md, matching T010.
U1: define ImportSummary in orchestration/price_import.py and re-export
it from run.py.
U2: print "All transactions are valued." only when at least one
transaction is recorded; state this in contracts/cli.md and add the
empty-database case to T017.

Change nothing unrelated.

## What Came Back
I applied everything you listed. tasks.md still has 43 tasks, with the same numbers.

Spec:
- SC-012 is removed.
- SC-007 is replaced with your wording: default pacing stays within the published limits for 
  keyless and Demo-key use, and if a rate-limit refusal still happens, no price is lost and 
  a later run continues (FR-009, SC-004).                                                       
- A new Clarifications entry records both changes.
- One edit you didn't ask for: an Assumption still required planning to pick a lookup method 
  "that meets SC-012." I cut that clause so it doesn't point at a criterion that no longer   
  exists. Nothing else in the spec changed.                                                  
                                                                                             
Pacing (research R1, plan, data model, config contract, quickstart):                         
- With a key (Demo or Pro), the default interval is now 2.5 s, about 24 requests a minute. That
  stays under even the older 30-a-minute Demo figure, whatever CoinGecko's current limit is. 
  The reasoning is in research R1.                                                           
- I kept the no-key default at 6.0 s. I read "about 2.5 seconds for the demo tier" as covering
  keyed runs only. The keyless limit is about 10–30 requests a minute and varies, so 2.5 s (24
  a minute) could draw refusals, and the new SC-007 says the defaults stay within keyless    
  limits too. Tell me if you meant 2.5 s for keyless runs as well.                           
- min_request_delay still overrides both defaults.                                           
- A full first year of prices now takes about 15 minutes with a key and about 36 minutes without,
  which research R1 notes is acceptable for a personal tool.

Tasks:
- T011: the default-interval check is now default_delay(True) == Decimal("2.5"). T024's pacing case expects at least 2.5 s with a key.
- SC-012 timing case: neither T024 nor T043 contained one. The only real timing expectation was the "about 4 min 20 s" line in quickstart §2, which T043 runs, and I replaced it.
- G1: marked no longer applicable.
- G2: T024 gains the comparison you described, for both the outage and the Ctrl-C cases. After the follow-up run, daily_prices (date, price, status) must match a fresh uninterrupted run on the same fake data, with both runs using the same fixed clock.
- G3: accepted with no new test, with your reasoning in a new "Analysis notes" bullet in the Notes section of tasks.md. That bullet also records how G1, G2, I1, I2, U1 and U2 were handled.

The four LOW fixes:
- I1: contracts/run-api.md now shows None defaults for the price source, clock and sleep, filled in when run() is called. I replaced the old "contract refinement" note in tasks.md to match.
- I2: the data model's Settings now includes import_prices: Path | None.
- U1: T020 defines ImportSummary in orchestration/price_import.py and re-exports it from run.py, creating that module early if US4 isn't done yet.
- U2: "All transactions are valued." is printed only when at least one transaction is recorded. contracts/cli.md says so, and I applied it in three tasks:
  - T007/T008: all_days_final returns False for an empty database.
  - T017: tests the empty-database case.
  - T022: prints the line only when that check is True.

The next step is /speckit-implement, or /speckit-analyze again first if you want a clean pass on record.
