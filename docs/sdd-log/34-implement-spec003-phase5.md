# 34 - Implement Spec 003, Phase 5

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-26

## Prompt
/speckit-implement Phase 5 only.  Stop after Phase 5
so I can review, run the gates, and commit.

## What Came Back
Phase 5 is done: you can now choose where the export goes with --reports-path, the reports_path config key, or the default ~/reports. T025–T027 are marked [X] and I've stopped there. All five gates pass: 392 tests, 96.29% coverage. Nothing is committed.

Tests
- T025 tests/integration/test_export_location.py runs these cases through run():
  - the default, <HOME>/reports;
  - the config key choosing the directory;
  - the option overriding the config key (the config directory is never created);
  - a missing nested directory being created;
  - ~ expansion;
  - a relative path resolving against the current directory, with an absolute path reported;
  - three invalid settings, each failing with the exact message before the wallet is contacted: reports_path = 5, reports_path = "" in the file, and an empty --reports-path;
  - a filesystem without locking, which gives the full message and leaves no export or temporary file.
- T026: --reports-path /x/y is now part of the existing test that maps options onto CliOptions. Omitting the option was already covered by test_no_options_means_all_none.

Implementation
- T027 cli.py: adds --reports-path after --db-path and passes it through as CliOptions.reports_path. It shows up in --help as "Directory for the xmr_income.csv export (default ~/reports)."

The location tests passed before T027 and never failed first. They exercise behaviour that Phases 2–4 already built; only the CLI mapping test failed beforehand.

Next is Phase 6 (US4): T028 is the reader documentation in docs/export-csv.md, T029 updates the README, and T030 cross-checks the documentation against the golden file.
