# 39 - Tasks for Spec 004 Income Summaries

**Command:** /speckit-tasks
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-27

## Prompt
/speckit-tasks

## What Came Back
The task list for feature 004 is written: 38 tasks in specs/004-income-summaries/tasks.md

All 38 tasks follow the required checklist format; I checked every line with a script.

┌─────────────────┬───────────┬───────┐
│      Phase      │   Tasks   │ Count │
├─────────────────┼───────────┼───────┤
│ 1 Setup         │ T001      │ 1     │
├─────────────────┼───────────┼───────┤
│ 2 Foundational  │ T002–T004 │ 3     │
├─────────────────┼───────────┼───────┤
│ 3 US1 (P1, MVP) │ T005–T015 │ 11    │
├─────────────────┼───────────┼───────┤
│ 4 US2 (P2)      │ T016–T020 │ 5     │
├─────────────────┼───────────┼───────┤
│ 5 US3 (P2)      │ T021–T025 │ 5     │
├─────────────────┼───────────┼───────┤
│ 6 US4 (P3)      │ T026–T033 │ 8     │
├─────────────────┼───────────┼───────┤
│ 7 Polish        │ T034–T038 │ 5     │
└─────────────────┴───────────┴───────┘

22 tasks are marked as safe to run in parallel. Each story's test tasks can run together, as can most of its implementation tasks. After US1, US2 and US4 can go in parallel. US3 shares cli.py with US4 and summary_format.py with US2, so those need coordinating.

How each story is tested on its own:
- US1: with output redirected, three summaries appear one after another after Exported …, with exact sums, zero rows for empty periods, and totals.
- US2: a provisional week shows *, an unpriced week shows ?, the totals show *?, and the legend explains both.
- US3: the contract example rendered at width W is side by side; at W − 1, or with no terminal, it's one after another, with identical figures.
- US4: on a machine set to UTC, a NY-midnight transaction moves between months depending on the config value and --timezone, and the option wins.

Suggested MVP: US1. It includes the whole FR-018 safeguard:
- Reading: T009 injects readers that raise StorageReadError("invalid stored price 'abc'") or RuntimeError.
- Unexpected data: T009 also injects records with a NaN price, a negative amount, or a status without a price.
- Rendering: T010 uses a malformed summaries object and a renderer patched to raise.

Each of these tests checks the earlier lines, the single error, exit status 1, and that the export on disk is the one this run wrote.

Points worth reviewing:
- Golden files: they're written by hand from the contract, like feature 003's. The side-by-side file is the contract's example word for word.
- Existing tests: T015 fixes any test that compares whole RunResults, since summaries is now set.
- Terminal width in CLI tests: CliRunner never reports a terminal, so these tests patch a small _terminal_width() helper in the CLI.
- A fix I made while checking: one golden record was dated after "today" and would have fallen outside every range, so I moved it to 2026-10-01 03:30 UTC (Sept 30 in New York).
- T038: the manual checks need your real wallet, so that one is yours.

Nothing is committed. Next step: /speckit-analyze, then /speckit-implement.

## Prompt
Use the rich library for the summary tables and the side-by-side layout,
as the original tool did. Declare rich as a direct dependency in
pyproject.toml. Update plan.md, research.md, the summary contract, and
tasks.md to match, replacing any hand-built table formatting. Render
into a rich Console with an explicit width in tests so output is
deterministic for golden files. Match the original tool's table style
(<box style, header style>). Change nothing unrelated.

## What Came Back
I've switched the plan to rich: each summary is a Table(box=box.ROUNDED, header_style="bold"), and the side-by-side layout is a rich grid. pyproject.toml now declares rich>=15.0.0 directly. It was already installed at 15.0.0 as Typer's dependency, so uv lock --offline only added the direct-dependency entry to uv.lock. Nothing is committed.

How rendering works now
- Each summary is built as a rich table. The rows are followed by a section rule and the Total row.
- The marks are part of the USD cell, padded so the figures stay aligned. A separate column would have added an extra border.
- Everything is rendered into an in-memory rich Console with an explicit width and returned as text, and the CLI prints that text. Highlighting and markup are turned off, so numbers aren't colored and labels aren't parsed.
- The CLI renders the complete text before printing anything, which keeps the FR-018 rule of no partial output.
- On a terminal, headers are bold. Redirected output has no ANSI codes.
- Tests render with an explicit width and no colour, so the golden files don't depend on the test machine's terminal.

What the prototype showed (rich 15.0.0, against the contract example)
- Width: side by side now needs 103 columns, up from 97. It switches exactly at 103/102. A typical wallet needs about 95, so an 80-column terminal gets the one-after-another layout.
- Height: 36 lines side by side, still within the spec's 40.
- Truncation: rich shortens figures to 0.250000000… when its console is narrower than a table. I specified that the console is always at least as wide as the layout, so a narrow terminal wraps lines instead of shortening figures.
- Trailing spaces: rich pads titles and grid cells with spaces. Golden comparisons strip trailing spaces per line; every visible character, including the box borders, is still compared exactly.

Three decisions for you to check
- Unicode borders: box.ROUNDED draws Unicode lines, so I dropped the contract's "every character is ASCII" rule. Figures, labels and marks are still ASCII.
- Bold header: I treated bold as not a colour, so the spec's "colors are out of scope" still holds.
- Title style: you specified only the box and header styles. I left the title at rich's default, centered and italic on a terminal. Tell me if the original tool's titles looked different.

Files updated
- On your list: plan.md, research.md (R7 rewritten for rich; R6, R9 and R10 adjusted), contracts/summaries.md (table rules, layouts, and the example replaced with the prototype's actual output), and tasks.md (still 38 tasks; T001, T006, T007, T010, T012, T014, T017, T018 and T020–T024 rewritten, plus T034 and the shared rules).
- Not on your list, but they declared the old rendering API:
  - contracts/run-api.md: now uses render_text and summary_text.
  - data-model.md: now uses the same two names.
  - quickstart.md: the wide terminal is now 110 columns, and step 3 checks for no ANSI codes instead of no trailing spaces.

I didn't change the spec.
