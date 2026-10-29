# 42 - Implement Phase 3 for Income Summaries

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-28

## Prompt
/speckit-implement Feature 004 (income summaries), Phase 3 only. 
Stop after Phase 3 so I can review, run the gates, and commit.

## What Came Back
Phase 3 is done (T005–T015 marked [X]), and I've stopped there. All five gates pass: 463 tests, 96.86% coverage. Nothing is committed.

What a run does now: after the Exported … line it prints a blank line, then the weekly, monthly and annual summaries one after another in the machine's time zone. With no transactions recorded, it prints No transactions to summarize yet. instead. If the summary step fails at any stage, the earlier lines still print, followed by one Error: line, and the run exits with status 1. The export file is left as written.

Tests first (T005–T010). All six new test files failed before the implementation existed, and all pass now:
- Aggregation: labels and ranges, local dates, exact sums, the daylight-saving and week-split cases, and the record checks.
- Formatting: number formats, the rich table style, plain versus styled output, no truncation, and checks on malformed input.
- Golden files: summaries_unmarked.txt and summaries_empty.txt. I generated the unmarked one from the planning prototype, not the new code, and checked its figures by hand: $265.00, $188,069.90 and $115.86, with totals of $188,450.77 and $188,520.77. The test's docstring records the arithmetic. The implementation's output matches it exactly.
- run() integration: the summaries match the export's data, failures before the export build no summaries, and the summary step changes nothing in the database.
- FR-018 failures in run(): reading and computing each give one clean error with the export kept, and Ctrl-C still propagates.
- CLI: where the summaries go in the output, plus three failure paths with no traceback.

Implementation (T011–T014):
- T011, summary.py: aggregation, with a check of every record before anything is summed.
- T012, summary_format.py: the rich tables, rendered only into an in-memory console, plus the guarded summary_text.
- T013, run.py:
  - The summary read runs on the same connection, right after the export's read, with no commit in between, so both see the same data.
  - A failure at this stage is held until the export is written, then raised as SummaryError.
- T014, cli.py: the summary text is rendered in full before anything is printed. _terminal_width() returns None for now; Phase 5 (US3) fills it in.

T015: no existing test broke, so nothing needed fixing.

Where I departed from the task text: T005 says "a record dated after today counts in nothing". The spec's edge case says "dated after the current period". A date later this year is still inside the current year, so it correctly counts in that year's row. I followed the spec and tested with a 2027 date instead. You may want to reword T005 to match.

## Notes
Reviewed updated and new files.  No changes needed.
Ran all gates manually.  All passed.
