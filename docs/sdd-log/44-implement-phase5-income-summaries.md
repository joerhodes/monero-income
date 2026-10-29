# 44 - Implement Phase 5 for Income Summaries Feature

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-28

## Prompt
/speckit-implement Feature 004 (income summaries), Phase 5 only. 
Stop after Phase 5 so I can review, run the gates, and commit.

## What Came Back
I've finished Phase 5 (T021–T025, marked [X]) and stopped there. A terminal at least W columns wide now shows weekly on the left with monthly above annual on the right, and anything narrower, or redirected output, gets the one-after-another layout. All five gates pass: 500 tests at 96.95% coverage, and ruff, mypy and lint-imports are clean. Nothing is committed.

I haven't run it in a real terminal. The only check of ANSI codes reaching a real terminal is a test that stands in for one (see below).

Pre-implement hook: the optional /speckit-git-commit pre-hook was offered and not run. The checklist requirements.md is 16/16 ✓ PASS.

Tests first (T021–T023). All three new test sets failed before the implementation existed:
- tests/unit/test_summary_format.py (contract example records):
  - W is weekly width + 4 + max(monthly, annual) widths, which is 103 for the example.
  - Width 200 and 103 give side by side; 102 and None give one after another.
  - At 102 the text is the same as with no terminal, ignoring trailing spaces.
  - Shape: the monthly table starts at column 54, and annual's title sits one blank line below monthly's bottom border, centred as on its own. Below the right column only the weekly table remains, then the legend.
  - No line is wider than the width given, and the output is at most 40 lines.
  - All 47 period and total rows and the legend appear the same in both layouts.
- tests/golden/summaries_side_by_side.txt: copied straight from the contract's side-by-side example, not from the code's output. It is checked at width 200, ignoring trailing spaces, and the code's output matches it.
- tests/cli/test_cli_success.py:
  - A wide terminal (200) gives side by side with bold headers.
  - A narrow one (60) gives one after another.
  - No terminal gives no ANSI codes.
  - _terminal_width() returns None when stdout isn't a terminal, and COLUMNS (123) when it is.

Implementation (T024–T025):
- summary_format.py:
  - side_by_side_width() computes W.
  - When the width is at least W, summary_renderable builds a Table.grid(padding=(0, TABLE_GAP, 0, 0)) with the weekly table in one cell and monthly, a blank line and annual in the other. The legend is appended as before.
  - I added two small helpers, _tables and _side_by_side_width, so the three tables are built once per render.
- cli.py: _terminal_width() returns shutil.get_terminal_size().columns when sys.stdout.isatty(), and None otherwise.

Something to review: typer.echo (click) strips ANSI codes whenever its output isn't a terminal. So the two styled CLI tests call runner.invoke(..., color=True) to stand in for a terminal. In real use the two agree: a terminal gets a width and keeps the codes, and redirected output gets no width and is plain text anyway.

The only other fix was rewrapping a docstring line that was too long for ruff.

## Notes
Reviewed all updated files.  No changes needed.
Manually ran gates.  All passed.
