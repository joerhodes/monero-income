# 33 - Implement Spec 003, Phase 4

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-26

## Prompt
/speckit-implement Phase 4 only.  Stop after Phase 4 
so I can review, run the gates, and commit.

## What Came Back
Phase 4 (US2) is done: tasks T020–T024 are marked [X], and I've stopped there as you asked. Before the implementation, 13 of the new tests failed. After it, all five gates pass: ruff check, ruff format, mypy, import-linter, and pytest with 375 tests at 95.80% coverage. The golden files are unchanged (checksums match), and nothing is committed.

Tests (T020–T022)
- tests/adapters/test_export_file.py gains cases for:
  - a disk-full error partway through the write, and Ctrl-C partway through;
  - the same two failures when there's no previous export;
  - cleanup of a leftover temporary file, with an unrelated file left alone;
  - owner-only permissions on the temporary file and the final file, even when the old export was 0o644;
  - a held lock making a second write wait until it's released;
  - a reports path that's a file, and a read-only directory (skipped when running as root);
  - the three "locking not supported" error codes, plus a different lock error that must stay a plain write error.
- tests/integration/test_export_failures.py checks two things. A run that can't write the export fails with the exact message from the CLI contract, the previous export is unchanged, and that run's transactions are still recorded. A Ctrl-C during the write propagates and also keeps the previous export.
- tests/cli/test_cli_errors.py: an export failure prints only the Error: line, with nothing on stdout, and exits 1. The existing parametrized test already covered Ctrl-C exiting 130, so I didn't add another.

Implementation
- T023 (src/monero_income/primitives/export_file.py): write_export now:
  - creates the reports directory, opens it and takes an exclusive lock;
  - deletes leftover temporary files;
  - writes and syncs a new temporary file, renames it over the export, then syncs the directory.

  If locking isn't supported, it raises ExportLockUnsupportedError before any temporary file exists. Any other OS error becomes ExportWriteError with the OS's own message. Any failure, including Ctrl-C, removes the temporary file, and Ctrl-C passes through unchanged.
- T024 (run.py): ExportWriteError becomes RunError("cannot write export <abs path>: <reason>. Recorded transactions and prices were kept; the previous export was not changed.").

Things you might notice in review
- Two of my new tests failed at first because of a mistake in the tests, not the code. The autouse isolated_home fixture creates tmp_path/home, so tmp_path is never empty. Those two tests now use a reports subdirectory.
- The lock-unsupported tests patch fcntl.flock by the string path "monero_income.primitives.export_file.fcntl.flock". That's the target the task names, and mypy rejects reaching fcntl through the module object.
- The lock-wait test uses threads, so I ran it 30 times to check it isn't flaky; it passed every time.
- export_db.py is still at 75% coverage: its two error paths (a database read error and an invalid stored price) have no tests.

Next is Phase 5 (US3): the --reports-path option and the reports-location tests (T025–T027).

## Follow Up
Implement the test for export_db.py

## What Came Back
I added tests for both error paths in export_db.py, and that file now has 100% coverage. All five gates pass: 382 tests, 96.29% total coverage.

Both tests are in tests/adapters/test_export_db.py:

- test_invalid_stored_price_is_a_read_error: a stored price that isn't a positive number raises StorageReadError with the message invalid stored price '<text>'. The daily_prices.usd_price column takes any text, so the test inserts the bad values directly with SQL. It runs six cases:
  - "abc" and "", which can't be parsed as a number;
  - "NaN" and "Infinity", which parse but aren't finite;
  - "0" and "-1.5", which aren't positive.
- test_database_error_is_a_read_error: querying through a closed connection raises a SQLite error, which export_records turns into StorageReadError.

The tool's own writes can never store an invalid price, so the first test can only set one up by bypassing them.

Nothing is committed.
