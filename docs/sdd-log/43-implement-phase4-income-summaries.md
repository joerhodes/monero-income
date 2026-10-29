# 43 - Implement Phase 4 for Income Summaries Feature

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-28

## Prompt
/speckit-implement Feature 004 (income summaries), Phase 4 only. 
Stop after Phase 4 so I can review, run the gates, and commit.

## What Came Back
I've finished Phase 4 (T016–T020, marked [X]) and stopped there. A USD figure now shows * when it uses a provisional price and ? when it leaves out an unpriced transaction. A legend follows the tables, listing only the marks that appear. All five gates pass: 484 tests at 96.91% coverage, and ruff, mypy and lint-imports are clean. Nothing is committed.

Tests first (T016–T018). I wrote these before the code. The new summary.py flag tests and the sequential golden file failed, and the format tests couldn't import LEGEND or marks yet. Two of the new tests passed from the start: "final prices flag nothing" and "flagged record outside the range flags nothing". The flags were always False before this phase, so those two will only catch later regressions.
- tests/unit/test_summary.py: 7 tests cover the provisional flag, the unpriced flag (with the price left out of USD), both flags together, a period with only unpriced records, and final prices only. They also check that each total's flags are the any of its rows, and that a flagged record outside the range flags nothing.
- tests/unit/test_summary_format.py:
  - the four mark combinations;
  - USD cells padded to the table's longest mark, still with 3 columns;
  - right alignment, checked against the contract's exact rows;
  - no extra text in tables without marks;
  - the exact legend text;
  - the legend's placement for both marks, * only and ? only;
  - no legend when nothing is marked;
  - the legend never wraps (the needed width is at least 54).
- tests/golden/summaries_sequential.txt: I copied it straight from the contract's one-after-another example, not from the tool's output, like the unmarked golden file. It is checked as a third case in test_summaries_golden.py. The code's output matches it line for line, ignoring trailing spaces.

Implementation (T019–T020):
- summary.py summarize: each period records whether it includes a provisional price or leaves out an unpriced transaction. A total is marked if any of its periods is.
- summary_format.py:
  - marks() returns the period's marks.
  - When a table has any mark, every USD cell ends with a space and its marks, padded to the table's longest mark.
  - LEGEND holds the contract's two lines.
  - summary_renderable appends a blank line and the legend lines for the marks shown. The width it asks for is at least the longest legend line.

The only fix needed was layout: ruff format rewrapped two calls in the format tests.

## Notes
Reviewed modified files.   No changes are needed.
