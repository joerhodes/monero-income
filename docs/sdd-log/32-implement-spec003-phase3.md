# 32 - Implement Phase 3 for Spec 003

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-26

## Prompt
/speckit-implement Phase 3 tests only (T007–T012). Stop before T013 so I
can review the golden files against contracts/export-csv.md.

## What Came Back
I've written the Phase 3 tests (T007–T012) and the two golden files, marked T007–T012 [X] in tasks.md, and stopped before T013 as you asked. Nothing is committed.

The new tests fail as intended, because the export code doesn't exist yet. That means three of the gates are red if you run them now:
- pytest: 313 passed, 13 failed, and 3 test files can't load. The failures are runs that produce no export and CLI output with no Exported line. The three files can't load because they import the modules T013–T015 will create.
- mypy: errors on those three missing modules.
- ruff check: three import-sorting errors (I001). Ruff treats a module it can't find as third-party. I confirmed this by adding empty placeholder modules: ruff then passed with no errors, and I deleted them afterwards. Running ruff --fix now would put the imports in the wrong place.

Some new tests already pass, which is expected now and meaningful later. These are the checks that a failed run leaves the previous export unchanged, and that no Exported line is printed when there's no export. They pass trivially until runs start writing the file.

Golden file for review: tests/golden/xmr_income.csv

I wrote it by hand from contracts/export-csv.md. To check the money values I computed them separately with high-precision Decimal arithmetic and half-up rounding, not with the tool's code. Every line ends in LF, including the last, and there's no byte-order mark. The prices are:
- 10-17: final 152.3456
- 10-18: final 152.345
- 10-19: final 150, stored through the import path
- 10-20: no price
- 10-25: provisional 163.40000000000001

The test inserts the transactions out of order, so the export's own sorting is what gets tested.

┌─────┬─────────┬──────────────────────┬───────────────────┬────────────────────┬─────────────┬───────────┬─────────────────────────────────────────┐
│  #  │ height  │    timestamp_utc     │        xmr        │     usd_price      │   status    │ usd_value │             What it covers              │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 1   │ 3530000 │ 2026-10-17T14:03:05Z │ 1.234567890123    │ 152.3456           │ final       │ 188.08    │ Contract example row 1 (exact value     │
│     │         │                      │                   │                    │             │           │ 188.0809859…)                           │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 2   │ 3530699 │ 2026-10-18T09:12:44Z │ 0.500000000000    │ 152.345            │ final       │ 76.17     │ Same second as row 3; the lower height  │
│     │         │                      │                   │                    │             │           │ sorts first                             │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 3   │ 3530700 │ 2026-10-18T09:12:44Z │ 1.000000000000    │ 152.345            │ final       │ 152.35    │ Exactly half a cent (152.345), rounds   │
│     │         │                      │                   │                    │             │           │ up                                      │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 4   │ 3531400 │ 2026-10-19T00:00:00Z │ 0.000000000001    │ 150                │ final       │ 0.00      │ 1 piconero; price stored as 150;        │
│     │         │                      │                   │                    │             │           │ midnight                                │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 5   │ 3531450 │ 2026-10-19T02:30:00Z │ 1234.500000000000 │ 150                │ final       │ 185175.00 │ Over 100,000 USD, with no thousands     │
│     │         │                      │                   │                    │             │           │ separators                              │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 6   │ 3532200 │ 2026-10-20T12:00:00Z │ 0.250000000000    │ TBD                │ TBD         │ TBD       │ Later block than row 7 but earlier      │
│     │         │                      │                   │                    │             │           │ time, so it comes first                 │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 7   │ 3532100 │ 2026-10-20T18:45:10Z │ 0.731000000000    │ TBD                │ TBD         │ TBD       │ Day with no price                       │
├─────┼─────────┼──────────────────────┼───────────────────┼────────────────────┼─────────────┼───────────┼─────────────────────────────────────────┤
│ 8   │ 3539000 │ 2026-10-25T11:00:00Z │ 2.000000000000    │ 163.40000000000001 │ provisional │ 326.80    │ Provisional; long-precision price       │
└─────┴─────────┴──────────────────────┴───────────────────┴────────────────────┴─────────────┴───────────┴─────────────────────────────────────────┘

The txids are SHA-256 of golden-1 to golden-8. The test runs with a fake clock set to 2026-10-26 and a price source that has no price for any day. So the provisional price stays as stored and 10-20 stays TBD.

The second golden file, tests/golden/xmr_income_empty.csv, is the header line followed by one LF and nothing else.

Other choices to look at

- Database-unchanged test (tests/integration/test_export.py): it wraps run_module.read_export_rows to compare the transactions and prices tables before and after the export read. That fixes the name and location T016/T017 must use: a read_export_rows imported into run.py.
- Same-second tiebreak: the golden file doesn't include two transactions with the same second and the same height, so the txid tiebreak isn't exercised there. The unit test in tests/unit/test_export_format.py covers it.
- Contract example rows: the golden file keeps all six example rows with their values unchanged; only the txids are filled in. Rows 2 and 6 are the extra cases from research R8.
- Line endings in git: there's no .gitattributes protecting the golden files from line-ending conversion. Adding tests/golden/* -text would protect their bytes on a checkout with CRLF conversion turned on. It's a small change, but outside these tasks, so I left it for you.

## Notes
I reviewed the generated golden files.  They are as expected.
Added `.gitattributes` as recommended

## Prompt
/speckit-implement Continue Phase 3 from T013. Tests T007–T012 are done,
and I have reviewed the golden files: treat tests/golden/ as correct and
do not modify it. If a golden test fails, fix the implementation; if you
believe a golden file is wrong, stop and tell me why instead of changing
it. Stop after Phase 3.

## What Came Back
Phase 3 is finished: tasks T013 through T019 are marked [X], and I've stopped there as you asked. All five gates pass, with 359 tests and 95.57% coverage. Both golden-file tests pass, and I didn't touch tests/golden/: the files' checksums match what I recorded before starting. Nothing is committed.

What I built
- T013 src/monero_income/orchestration/export_format.py: the formatting and sorting functions. They take plain values and do no I/O. Rounding to the cent uses a precision sized to each value, so very large products don't overflow.
- T014 src/monero_income/primitives/export_db.py: export_records, the single read-only query. It raises StorageReadError on a database error or on a stored price that isn't a positive number.
- T015 src/monero_income/primitives/export_file.py: write_export, the first version. It writes an owner-only temporary file, syncs it to disk, then renames it over the old export. Locking, cleanup of leftover temporary files, and error translation come in T023 (Phase 4).
- T016 src/monero_income/orchestration/export.py: the export step, with read_export_rows and write_export_file kept separate.
- T017 run() in run.py: it reads the rows before closing the database. It writes the file after closing it, inside the existing error handling, so any earlier failure means no export is written.
- T018 cli.py: prints Exported N transaction(s) to <path>. as the last line.
- T019: no existing test broke.

Gap in the tests: the two error paths in export_db.py have no tests, which leaves that file at 75% coverage. They handle a database read error and a stored price that's invalid, which the tool's own writes can't produce. T008 didn't list either case. I didn't add tests because you'd marked T007–T012 as reviewed. If you want them, it's two short tests in tests/adapters/test_export_db.py.

Your .gitattributes has a typo: it reads test/golden/* -text, but the directory is tests/golden/, so the rule protects nothing right now. I left it for you to fix.

Next is Phase 4 (US2): T020–T022 add the failure, interrupt, lock and permissions tests, then T023 hardens write_export and T024 maps write failures to the run error message.
