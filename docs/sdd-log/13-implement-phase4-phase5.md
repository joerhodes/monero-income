# 13 - Implement Phase 4 (User Story 2) and Phase 5 (User Story 3)

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-16

## Prompt
/speckit-implement Phase 4 (US2) and Phase 5 (US3) only. Stop after
Phase 5 so I can review, run the gates, and commit.

## What Came Back
Phases 4 (US2) and 5 (US3) are done: T033–T046 are marked [X] in tasks.md, and only Phase 6 
polish (T047–T050) is left. I've stopped there, and nothing is committed.                   

All five gates pass under Python 3.13.13:

┌──────────────────────────────────┬────────────────────────────┐
│               Gate               │           Result           │
├──────────────────────────────────┼────────────────────────────┤
│ ruff check / ruff format --check │ pass                       │
├──────────────────────────────────┼────────────────────────────┤
│ mypy (strict)                    │ no issues in 43 files      │
├──────────────────────────────────┼────────────────────────────┤
│ lint-imports                     │ 2 contracts kept           │
├──────────────────────────────────┼────────────────────────────┤
│ pytest                           │ 120 passed, coverage 94.5% │
└──────────────────────────────────┴────────────────────────────┘

I also ran the real command against a port with nothing listening (with HOME pointed at a
scratch directory). It printed Error: cannot reach the wallet at
http://127.0.0.1:59999/json_rpc: [Errno 61] Connection refused, exited with 1, and showed no
traceback.

Phase 4, re-syncing:
- Resuming: each run now starts 61 blocks below the last recorded height, which re-reads the
  last 60 blocks to catch reorgs. Transaction ids already in the database are skipped, and a
  window with nothing new isn't written at all.
- Output: the CLI prints No new transactions found. when there's nothing new.
- Tests:
  - a second run changes nothing in the table;
  - only a genuinely new entry is added;
  - an entry re-mined 30 blocks lower is neither duplicated nor changed;
  - the second run's first window is exactly (939, 10939];
  - an empty wallet records nothing;
  - a run with nothing new over 10,000 recorded rows finishes in under 5 seconds (SC-006).

Phase 5, interruptions and errors:
- Rollback: sync() rolls back the window in progress on any exception, including Ctrl-C. Earlier windows stay committed.
- Error messages: run() turns each config, storage and wallet error into the matching message from contracts/cli.md. Ctrl-C passes straight through to the CLI.
- CLI exit codes: errors print one Error: line and exit 1. Ctrl-C prints "interrupted; anything already recorded was kept" and exits 130. Anything unexpected prints Error: unexpected <Type>: … and exits 1.
- Tests:
  - a wallet failure on window 3 keeps windows 1–2, and the next run's table equals a single uninterrupted run;
  - Ctrl-C leaves no lock and keeps window 1;
  - an insert that overflows mid-window stores neither of that window's rows;
  - a second run started while another holds the write lock fails cleanly with nothing lost;
  - every error category is covered, and none of the messages contains the password or the word "transfer".

Things to note:
- tests/integration/helpers.py is new and wasn't in the task list. It holds run_once() and table(), which the resync, interruption, performance and concurrency tests share.
- The Ctrl-C test already passed before T044. insert_records already rolls back on any exception, and run() closes the connection. The new rollback in sync() also covers a failure while fetching or parsing a window, before any insert starts.
- Running the real command creates an empty database before contacting the wallet. That's why xmr.db appeared in the scratch directory even though the wallet couldn't be reached. This is the designed order (settings, then database, then wallet), so a later run picks up from it.

## Notes
All gates run cleanly.
All code and tests pass an initial sniff test - nothing jumps out.
