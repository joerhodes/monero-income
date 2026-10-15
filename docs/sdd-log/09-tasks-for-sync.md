# 09 - Tasks for Sync Feature

**Command:** /speckit-tasks
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-15

## Prompt
/speckit-tasks

## What Came Back
I wrote specs/001-sync-incoming-transactions/tasks.md with 47 tasks. All of them match the required checklist format, and 27 are marked as able to run in parallel.

┌──────────────┬────────────┬─────────────────────────────────────────────────────────────┐
│    Phase     │   Tasks    │                      What it delivers                       │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│              │ T001–T005  │ pyproject.toml, tool settings (90% coverage,                │
│ 1 Setup      │ (5)        │ --disable-socket, import-linter layering rules), package    │
│              │            │ skeleton, .gitignore for database and config files          │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 2            │ T006–T021  │ Data types, schema and storage, wallet RPC client and       │
│ Foundational │ (16)       │ response parsing, config file reading and settings, fake    │
│              │            │ wallet for tests                                            │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 3 US1 (P1)   │ T022–T030  │ First run records every incoming transaction, in            │
│ MVP          │ (9)        │ 10,000-block windows, combined by transaction id            │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│              │ T031–T037  │ Resume from last recorded height minus 60, skip             │
│ 4 US2 (P2)   │ (7)        │ already-recorded ids, "No new transactions found.", SC-006  │
│              │            │ performance test                                            │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│              │ T038–T043  │ Rollback of the window in progress, translation of every    │
│ 5 US3 (P3)   │ (6)        │ error into a message, Ctrl-C and unexpected errors in the   │
│              │            │ CLI with no traceback                                       │
├──────────────┼────────────┼─────────────────────────────────────────────────────────────┤
│ 6 Polish     │ T044–T047  │ Test that no message says "transfer", README usage section, │
│              │ (4)        │  all quality checks, manual check against a stagenet wallet │
└──────────────┴────────────┴─────────────────────────────────────────────────────────────┘

How each story is tested on its own:
- US1: a first run against the fake wallet, with entries spread over three windows and one transaction paid to two subaddresses, stores every transaction id once with exact values.
- US2: a second run with no wallet changes records 0 and leaves the table identical; an overlapping entry is never duplicated.
- US3: if the wallet fails on its third request, windows 1–2 stay saved, and the next run gives the same table as one uninterrupted run.

Tests are included. The spec doesn't ask for them, but constitution v1.2.0 effectively does: Principle VII sets a 90% coverage floor, and Principle V requires every external service behind a fake. Each story writes its tests first.

One contract fix: contracts/run-api.md defaults the wallet factory to HttpWalletRpc.from_settings. That would make primitives depend on orchestration's Settings, which breaks the layering rule (Principle I). T016 and T028 put the factory in orchestration as make_wallet instead, and the note at the end of tasks.md records this. The contract file itself still shows the old default; I didn't edit it.

Suggested MVP: Phases 1–3 (T001–T030), then check quickstart §3 "First run" against a stagenet wallet.
