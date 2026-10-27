# 29 - Tasks for Transaction Export

**Command:** /speckit-tasks
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-26

## Prompt
/speckit-tasks

## What Came Back
I've written specs/003-transaction-csv-export/tasks.md: 34 tasks, each with a checkbox, ID, story label where needed, and file path.

I included test tasks, which the task template treats as optional, because the constitution requires a 90% coverage floor and golden-file tests for report output. Each story's tests come first and should fail before the implementation goes in.


┌────────────────────────────────┬───────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│             Phase              │ Tasks │                                            Story's own check                                            │
├────────────────────────────────┼───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Setup                          │ 1     │ Run the five checks (lint, format, type check, import rules, tests) before any change                   │
├────────────────────────────────┼───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Foundational                   │ 5     │ Error type, ExportRecord, reports_path setting and its tests, ExportSummary                             │
├────────────────────────────────┼───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ US1: export after each run     │ 13    │ Three transactions on two days give the file with the header and three rows in time order; the unpriced │
│ (P1, MVP)                      │       │  row shows TBD three times                                                                              │
├────────────────────────────────┼───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ US2: never a broken export     │ 5     │ A write that fails partway leaves the old file byte-for-byte unchanged, no temporary file remains, and  │
│ (P1)                           │       │ the run exits 1                                                                                         │
├────────────────────────────────┼───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ US3: choose the folder (P2)    │ 3     │ The default, the config key, and the command-line option each put the file in the right folder          │
├────────────────────────────────┼───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ US4: reader docs (P3)          │ 3     │ Using only docs/export-csv.md, a reader can explain every column and recompute usd_value                │
├────────────────────────────────┼───────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Polish                         │ 4     │ Round-trip test for exactness, all checks passing, then quickstart by hand                              │
└────────────────────────────────┴───────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

Running in parallel: the six US1 test tasks can be written together, and so can its three new modules. Once US1 is in, US2, US3 and US4 can proceed in parallel. US2 and US3 both touch run.py and cli.py lightly, so those two files need coordinating.

Decisions in the tasks you might want to check:
- US1 already writes safely: it writes a temporary file and swaps it in, so even the MVP never cuts an existing export short. US2 adds the folder lock, cleanup of leftovers from killed runs, and turning write errors into a failed run. Ship US1 and US2 together; both are P1.
- Golden files written by hand: the expected tests/golden/ files must be written from the format contract, not copied from the program's output. Otherwise a formatting bug would get locked in as correct.
- Existing tests: every run now writes an export into the test's temporary home folder. T019 adjusts any existing test that this breaks; it doesn't turn the export off.
- README: T029 replaces "CSV output and summaries come in later features" with "Summaries come in a later feature."

Suggested MVP: Phases 1–3, then quickstart steps 1–6. Next, run /speckit-analyze (your workflow puts it before implementation), then /speckit-implement.
