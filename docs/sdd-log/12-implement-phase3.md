# 12 - Implement Phase 3 - User Story 1

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-16

## Prompt
/speckit-implement Phase 3 (US1) only. Stop after Phase 3 so I can
review, run the gates, and commit.

## What Came Back
Phase 3 (US1, the MVP) is done: T024–T032 are marked [X] in tasks.md. I've stopped before Phase 4, and nothing is committed.

All five gates pass under your pinned Python 3.13.13:

┌──────────────────────────────────┬───────────────────────────┐
│               Gate               │          Result           │
├──────────────────────────────────┼───────────────────────────┤
│ ruff check / ruff format --check │ pass                      │
├──────────────────────────────────┼───────────────────────────┤
│ mypy (strict)                    │ no issues in 36 files     │
├──────────────────────────────────┼───────────────────────────┤
│ lint-imports                     │ 2 contracts kept          │
├──────────────────────────────────┼───────────────────────────┤
│ pytest                           │ 91 passed, coverage 94.2% │
└──────────────────────────────────┴───────────────────────────┘

uv run monero-income --help shows the three options, no --password and no subcommands.

Built in this phase:
- transform.py: splits the chain into 10,000-block windows and combines entries that share a
  transaction id, summing their amounts.
- sync.py: fetches each window, parses and combines it, then inserts and commits that window
  before fetching the next. For now it always starts at height 0; US2 changes that.
- run.py: resolves settings (sending warnings to the reporter), opens the database, builds the
  wallet client, syncs, and closes both the wallet and the database. It also holds Reporter,
  SyncResult and make_wallet.
- cli.py: replaces the placeholder with a single Typer command and its three options. It prints
  Recorded N new transaction(s).
- Tests:
  - The first-sync test runs run() against the fake wallet across three windows. It checks exact amounts (including 123456789012), one transaction split across two subaddresses, a block exactly on a window edge, and the UTC date.
  - Persistence tests cover a database in a directory that doesn't exist yet, and the default path under the redirected HOME.
  - CLI tests check the output lines and how the options are passed through.

Expected gaps until later phases:
- Running the tool twice on the same database fails. The second run tries to re-insert the same transaction ids and gets a database write error. US2 (T037–T038) adds resuming from the last recorded height and skipping already-recorded ids.
- Errors still show raw tracebacks. That includes running the real command with no wallet listening, which gives a connection-error traceback. US3 (T043–T045) turns every error into an Error: … line with the right exit code.
- No "No new transactions found." message yet. T039 in US2 adds it.

Added beyond the task list:
- tests/fakes/reporter.py: a ListReporter that collects warnings, which run() needs in tests.
- Closing the wallet client: run() calls the HTTP client's close() if the wallet has one. close() isn't part of the WalletRpc protocol, so the fake doesn't need it.

Untracked for you to review and commit: the new files under src/ and tests/, plus the tasks.md updates.

## Notes

All gates run cleanly.
All code and tests pass an initial sniff test - nothing jumps out.
