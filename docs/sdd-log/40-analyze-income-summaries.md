# 40 - Analyze Tasks Income Summaries (Spec 004)

**Command:** /speckit-analyze
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-28

## Prompt
/speckit-analyze

## What Came Back
Specification Analysis Report

Verdict: no critical issues, but fix one high-severity issue (I1) before /speckit-implement. As written, T012 and T013 create a circular import. Everything else is medium or low. Every functional requirement and success criterion maps to at least one task, and the constitution check is clean.

ID: I1
Category: Inconsistency
Severity: HIGH
Location(s): tasks.md:77 (T003), :242–243 (T012), :259 (T013), :430
Summary: Circular import. summary_format.py imports SummaryError/RunResult from run.py (T012), and run.py uses summary_failure_message from
summary_format.py (T013: "run.py uses the same helper"). Importing either module will fail.
Recommendation: Move summary_failure_message to orchestration/summary.py, which both modules already import. Or define SummaryError in
orchestration/errors.py, with RunResult imported only for type checking. Update T003, T012, T013, data-model.md and run-api.md to match.
────────────────────────────────────────
ID: C1
Category: Coverage
Severity: MEDIUM
Location(s): spec.md:348 (SC-007); tasks.md:401 (T034)
Summary: SC-007 is "showing the summaries adds less than one second to the run". T034 times only build_summaries and render_text, not the summaries'
second database read of 100,000 rows (research R1).
Recommendation: Time a run() with the default summary_reader against one with a reader returning [], over 100,000 recorded rows, and assert the
difference is under 1 s. Or add the export_records read to T034's timing.
────────────────────────────────────────
ID: C2
Category: Coverage
Severity: MEDIUM
Location(s): spec.md:311 (FR-019); tasks.md T008, T013
Summary: Agreement between export and summaries depends on both reads sharing one snapshot (no commit between them). T013 states this, but no task tests
it. T008 only compares results after the run.
Recommendation: Add a T009 case: a summary_reader that commits a new transaction on a second connection before calling export_records, then assert the
summaries don't include it. Or assert conn.in_transaction inside the reader.
────────────────────────────────────────
ID: C3
Category: Coverage
Severity: MEDIUM
Location(s): plan.md (Testing: "local-midnight cases on both sides of a DST change"); tasks.md T005
Summary: The plan promises midnight cases on both sides of a daylight-saving change. T005 covers only 2026-11-01T03:30Z, still on summer time (EDT).
Recommendation: Add 2026-11-02T04:30:00Z (23:30 EST on Nov 1, after the change) to T005's local_date and build_summaries cases.
────────────────────────────────────────
ID: U1
Category: Underspecification
Severity: MEDIUM
Location(s): tasks.md T007, T018
Summary: The unmarked and sequential golden files are "from contracts/summaries.md", but the contract only shows the side-by-side example. Drawing box
tables by hand isn't practical. The writer would end up copying the tool's own output, which defeats the golden check feature 003 relied on.
Recommendation: State how they're produced: from the rich prototype script with the contract's settings, not from the implementation. Then check them by
hand against the figures in the contract's notes. Or add the sequential example to the contract.
────────────────────────────────────────
ID: U2
Category: Underspecification
Severity: LOW
Location(s): tasks.md T012 (summary_text), T010
Summary: result.exported is ExportSummary | None. Reading .path fails mypy --strict, and crashes if a CLI test's FakeRun sets summaries but not
exported.
Recommendation: Require exported whenever summaries is set (an assert or a guard). Say that T010's fakes set both.
────────────────────────────────────────
ID: U3
Category: Underspecification
Severity: LOW
Location(s): contracts/summaries.md; research R7
Summary: The title style is left at rich's default (centered, italic on a terminal). The spec and your request name only the box and header styles.
Recommendation: Confirm the default matches the original tool, or name a title style.
────────────────────────────────────────
ID: I2
Category: Inconsistency
Severity: LOW
Location(s): plan.md (Project Structure) vs tasks.md T007, T028
Summary: The tasks create tests/integration/test_summaries_golden.py and tests/integration/test_summary_timezone.py, which aren't in the plan's file
tree.
Recommendation: Add both to the plan's tree.
────────────────────────────────────────
ID: I3
Category: Inconsistency
Severity: LOW
Location(s): research.md:246 (R8)
Summary: R8 says "When transactions is 0, the CLI prints the no-transactions message". Under the rich design, render_text produces it (T012).
Recommendation: Reword: "the renderer shows the no-transactions message".
────────────────────────────────────────
ID: C4
Category: Coverage
Severity: LOW
Location(s): spec.md (edge case: week split across months or years); tasks.md T005
Summary: No explicit case for a week spanning two months, where each transaction counts in its own month but both in one week.
Recommendation: Add a T005 case: 2026-08-31 and 2026-09-01 (both in 2026-W36) give one weekly row and two monthly rows.

Coverage Summary Table
┌───────────────────────────────────────┬───────────┬────────────────────────┬────────────────────────────┐
│            Requirement Key            │ Has Task? │        Task IDs        │           Notes            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-001 summaries after export         │ Yes       │ T008, T013, T014       │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-002 26/12/4 ranges                 │ Yes       │ T005, T011             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-003 ISO week/month/year labels     │ Yes       │ T005, T011             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-004 local date of each transaction │ Yes       │ T005, T011             │ DST, see C3                │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-005 time zone precedence           │ Yes       │ T008, T028, T031, T032 │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-006 invalid time zone              │ Yes       │ T026–T028, T030–T032   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-007 every period, zeros            │ Yes       │ T005, T006             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-008 columns and title              │ Yes       │ T006, T012             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-009 exact XMR, grouped             │ Yes       │ T005, T006, T011, T012 │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-010 exact USD, rounded once        │ Yes       │ T005, T006, T011, T012 │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-011 totals                         │ Yes       │ T005, T011             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-012 marks                          │ Yes       │ T016, T019             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-013 legend                         │ Yes       │ T017, T020             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-014 layout choice                  │ Yes       │ T021, T023–T025        │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-015 same content in both layouts   │ Yes       │ T021                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-016 no-transactions message        │ Yes       │ T006, T008, T010       │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-017 read-only                      │ Yes       │ T008                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-018 safeguard                      │ Yes       │ T009, T010, T012–T014  │ I1 blocks T012 and T013    │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-019 same data as export            │ Partial   │ T008, T013             │ Snapshot not tested (C2)   │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-020 earlier lines unchanged        │ Yes       │ T010, T015             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ FR-021 "transactions" wording         │ Yes       │ T035                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ SC-001                                │ Yes       │ T008, T010             │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ SC-002                                │ Yes       │ T005                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ SC-003                                │ Yes       │ T005                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ SC-004                                │ Yes       │ T016                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ SC-005                                │ Yes       │ T021                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ SC-006 ≤ 40 lines                     │ Yes       │ T021                   │                            │
├───────────────────────────────────────┼───────────┼────────────────────────┼────────────────────────────┤
│ SC-007 < 1 s at 100,000               │ Partial   │ T034                   │ Second read not timed (C1) │
└───────────────────────────────────────┴───────────┴────────────────────────┴────────────────────────────┘

Constitution Alignment Issues: none.
- I. Layered architecture: rich is third-party, outside the import-linter layers.
- II. Thin CLI: the CLI only measures the terminal and echoes pre-rendered text.
- III. Exact money: int piconero, an exact Decimal sum with Inexact trapped, rounded once at output.
- IV. Separate I/O from transformation: load_zone is a primitive, and rendering writes only to an in-memory console.
- V. Testable without the network: TZ is set through a fixture, and pytest-socket is unchanged.
- VI. Data safety: read-only, with no schema change.
- Workflow: golden files are new in this change.

Unmapped Tasks: none. T001 (baseline gates), T015 (test fix-ups), T036 (README), T037 (gates) and T038 (manual checks) are setup and polish.

Metrics
- Total requirements: 28 (21 FR + 7 SC)
- Total tasks: 38
- Coverage: 100% have at least one task; 26 fully covered, 2 partial (FR-019, SC-007)
- Ambiguity count: 2 (U1, U3)
- Duplication count: 0
- Critical issues: 0

Next Actions

- Before implementing: fix I1, either by editing T003, T012 and T013 by hand or by re-running /speckit-tasks after updating data-model.md and run-api.md.
- Worth doing now: C1, C2, C3 and U1 are each a small edit to tasks.md.
- Low priority: U2, U3, I2, I3 and C4 can be folded in at the same time or left.

Would you like me to suggest concrete remediation edits for the top 5 issues (I1, C1, C2, C3, U1)?

## Response
For I1 - Accept recommendation.

For C1 - Remove SC-007 from the spec. Summary display time is not a requirement
for this personal tool at its current scale. Add a Clarifications entry.
Then remove the timing case from T034 and resolve C1 as no longer
applicable. Change nothing unrelated.

For C2 - Resolve without a new test: the tool runs one instance at a time
(see the concurrent-run edge case), and export/summary agreement in
normal runs is covered by T008. Add to the spec's Assumptions that
agreement between the export and the summaries assumes no other process
writes to the database during a run. Change nothing else.

For C3 - Accept recommendation.
For U1 - Add the sequential example to the contract.
For U2 - Accept recommendation.
For U3 - Defaults match the original tool.
For I2 - I added files to the plan's tree.
For I3 - I updated R8.
For C4 - Accept recommendation.

## What Came Back
I've applied all ten resolutions. Writing out the one-after-another example also turned up a bug in the width rule, which I fixed too. Nothing is committed, and no tests ran because there's no code yet.

The bug: that layout is rendered at the tables' width, 50 columns. The legend line * includes a provisional price, which may still change is 54 characters, so rich would wrap it onto two lines. Now the width used is whichever is larger: the layout or the longest legend line shown. That makes the one-after-another example 54 columns wide. The tables themselves don't change, and side by side is still 103. This is now in tasks T017, T018 and T020, the contract, research R7 and the data model.

What changed for each item:
- I1: summary_failure_message moved into T002, so it lives in orchestration/summary.py. Both summary_format.py and run.py already import that module, which removes the circular import. T012, T013, the dependency notes and the data model match.
- C1:
  - SC-007 is removed from the spec, with a new Clarifications entry (Session 2026-10-28).
  - T034 was only the timing case, so I deleted the whole task. I didn't renumber, so Polish now goes T033 → T035 and existing references still point to the right tasks.
  - Three other places referred to the removed SC-007: the plan's Performance Goals and its test_performance.py line, and a sentence in research R1. I updated or removed them.
- C2: added the assumption to the spec. The concurrent-run edge case you mentioned is in feature 001's spec ("Second run started while one is in progress"), so the assumption cites that.
- C3: added to T005: 2026-11-01T03:30:00Z is 23:30 EDT on Oct 31 (before the change) and 2026-11-02T04:30:00Z is 23:30 EST on Nov 1 (after it). The test's today is 2026-11-10. I checked both conversions against zoneinfo.
- C4: added to T005: Aug 31 and Sep 1, 2026 are both in week 2026-W36. The test expects one weekly row and two monthly rows. Checked.
- U1: the contract now shows the full one-after-another example. It is the rich prototype's output, not hand-drawn, and its tables match the side-by-side ones line for line. T018's golden file now points to it.
- U2:
  - summary_text now first checks that a run that set summaries also set exported. If not, it raises ValueError, outside the FR-018 guard. That also satisfies mypy --strict.
  - T010's fake runs now set exported whenever they set summaries.
- U3, I2 and I3: no changes from me.

I edited spec.md, plan.md, research.md, data-model.md, tasks.md and contracts/summaries.md. Your earlier uncommitted changes to plan.md and research.md are still there.

## Prompt 
/speckit-analyze

## What Campe Back
Specification Analysis Report

Verdict: ready for /speckit-implement. There are no critical or high-severity issues, and every remaining requirement has at least one task. One medium issue (I1) comes from my own fix for U2 in the last round and is worth correcting before implementing; the other is a formatting nit.

ID: I1
Category: Inconsistency
Severity: MEDIUM
Location(s): tasks.md:245 (T012 summary_text); research.md:330–332 (R10 rationale)
Summary: My U2 fix has summary_text raise ValueError outside the guarded block when summaries is set but exported is not. That would print a traceback,
which research R10 rules out ("an unexpected bug in them must not … show a traceback"). run() never produces that case; only a badly built test fake
could.
Recommendation: Make the export path an explicit input: summary_text(summaries, export_path, width, styled). The CLI passes result.exported.path, which
it already has. Then there's no runtime check, mypy is satisfied by the signature, and T010's fakes need no special rule. Update T010, T012, T014,
run-api.md and data-model.md.
────────────────────────────────────────
ID: F1
Category: Formatting
Severity: LOW
Location(s): research.md:224
Summary: The line I edited is 117 characters; the surrounding prose wraps at about 92.
Recommendation: Rewrap R7's Width bullet.

Everything from the first analysis is resolved:
- I1 (circular import), C3, C4, U1 and U2 are fixed.
- C1 (SC-007 removed) and C2 (the new assumption) are resolved as you decided.
- U3, I2 and I3 needed no change from me.
- The legend-width bug is fixed consistently across T017, T018, T020, T024, the contract, research R7 and the data model.

I found no leftover references to SC-007, T034, test_performance.py or "needs 50".

Coverage Summary Table

┌─────────────────────────────────────┬───────────┬────────────────────────┬───────────────────────────────────────────────────┐
│           Requirement Key           │ Has Task? │        Task IDs        │                       Notes                       │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-001 summaries after export       │ Yes       │ T008, T013, T014       │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-002 26/12/4 ranges               │ Yes       │ T005, T011             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-003 labels                       │ Yes       │ T005, T011             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-004 local date                   │ Yes       │ T005, T011             │ Both sides of the clock change now covered        │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-005 time zone precedence         │ Yes       │ T008, T028, T031, T032 │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-006 invalid time zone            │ Yes       │ T026–T028, T030–T032   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-007 zero periods                 │ Yes       │ T005, T006             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-008 columns and title            │ Yes       │ T006, T012             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-009 exact XMR                    │ Yes       │ T005, T006, T011, T012 │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-010 exact USD                    │ Yes       │ T005, T006, T011, T012 │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-011 totals                       │ Yes       │ T005, T011             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-012 marks                        │ Yes       │ T016, T019             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-013 legend                       │ Yes       │ T017, T020             │ Legend is never wrapped                           │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-014 layout choice                │ Yes       │ T021, T023–T025        │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-015 same content in both layouts │ Yes       │ T021                   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-016 no-transactions message      │ Yes       │ T006, T008, T010       │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-017 read-only                    │ Yes       │ T008                   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-018 safeguard                    │ Yes       │ T009, T010, T012–T014  │ See I1                                            │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-019 same data as export          │ Yes       │ T008, T013             │ Concurrent writers are out of scope by assumption │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-020 earlier lines unchanged      │ Yes       │ T010, T015             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ FR-021 "transactions" wording       │ Yes       │ T035                   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ SC-001                              │ Yes       │ T008, T010             │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ SC-002                              │ Yes       │ T005                   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ SC-003                              │ Yes       │ T005                   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ SC-004                              │ Yes       │ T016                   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ SC-005                              │ Yes       │ T021                   │                                                   │
├─────────────────────────────────────┼───────────┼────────────────────────┼───────────────────────────────────────────────────┤
│ SC-006 ≤ 40 lines                   │ Yes       │ T021                   │                                                   │
└─────────────────────────────────────┴───────────┴────────────────────────┴───────────────────────────────────────────────────┘

Constitution Alignment Issues: none.
- I. Layered architecture: the helper move means summary.py imports neither run.py nor summary_format.py, so the orchestration modules no longer import each other.
- III. Exact money: unchanged.
- IV. I/O kept separate: unchanged.
- VII. Gates: T037 still runs all of them.
- I1 conflicts with research R10's stated rule, not with the constitution itself.

Unmapped Tasks: none. T001, T015 and T035–T038 are setup and polish. The task IDs go from T033 to T035 because T034 was deleted.

Metrics
- Total requirements: 27 (21 FR + 6 SC)
- Total tasks: 37
- Coverage: 100% (27 of 27 fully covered)
- Ambiguity count: 0
- Duplication count: 0
- Critical issues: 0

Next Actions

- I1: a small edit to T010, T012, T014, run-api.md and data-model.md, best done before /speckit-implement so T012 isn't written with the ValueError check.
- F1: rewrap one line in research R7.
- After that, run /speckit-implement.

Would you like me to suggest concrete remediation edits for the top 2 issues?

## Prompt
Resolve I1 by accepting the recommendation.
Mark F1 resolved.  I reformatted the long lines in R7.

## What Came Back
I1 is fixed and F1 is marked resolved. There's no ValueError check left, so nothing in the summary step can end in a traceback.

The guarded rendering function now takes the export's path as an explicit input: summary_text(result, export_path, width, styled). It still takes result, because the error it raises has to carry it. Since the function never reads the optional result.exported, it needs no runtime check, and mypy --strict is satisfied by the signature.

The CLI passes result.exported.path when exported is set. If it isn't, the CLI shows no summaries instead of raising. That can't happen in a real run, because run() always sets exported before summaries.

I updated every place that names the function:
- tasks.md: T012 (the signature, with the ValueError check removed), T014 (how the CLI calls it) and T010 (why the fake runs set exported).
- contracts/run-api.md: the signature and its docstring.
- data-model.md: the summary_text row.
- research.md: the Rendering row in R10's table.

A search finds no remaining uses of the old signature or the ValueError.

The analysis now has no open findings. Nothing is committed.
