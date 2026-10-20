# 24 - Implement Phase 6 for Spec 002

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-19

## Prompt
/speckit-implement Phase 6 (US4) only. Stop
after Phase 6 so I can review, run the gates, and commit.

## What Came Back
Phase 6 (US4, the optional CSV import) is done: T032–T038 are marked [X] in tasks.md, so all four user stories are implemented. I've stopped before Phase 7 (polish), and nothing is committed.

All five gates pass:

┌──────────────────────────────────┬──────────────────────────────────────────┐
│               Gate               │                  Result                  │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ ruff check / ruff format --check │ pass                                     │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ mypy (strict)                    │ no issues in 62 files                    │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ lint-imports                     │ 2 contracts kept                         │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ pytest                           │ 286 passed (up from 255), coverage 95.7% │
└──────────────────────────────────┴──────────────────────────────────────────┘

Built in this phase:
- price_import_file.py:
  - Reading: the file is read as UTF-8, and a leading BOM from spreadsheet exports is dropped.
  - Checking: the parser checks every row before anything is written, and the first problem rejects the whole file. Errors name the line, counting the header as line 1:
    - a wrong header;
    - an extra column;
    - a bad date, which must be exactly YYYY-MM-DD and a real date;
    - a missing price, or a price that isn't plain digits with an optional decimal part (so no exponents, signs, NaN or thousands separators);
    - a zero price;
    - a repeated date, as in "date 2024-03-01 already on line 4."
- price_import.py: select_imports keeps only rows older than the 364-day cutoff that have no recorded price, and counts the rest as skipped. import_prices inserts the kept rows as final prices with source import, all in one transaction.
- run.py: the import runs after a successful sync and before pricing. An invalid file becomes Error: cannot import prices from <path>: line N: <reason> with exit 1, before any lookup. Days the import fills are no longer needed, so they're never requested.
- cli.py: adds --import-prices CSV, and prints Imported N prices; skipped M rows. (with singular forms) between the sync line and the pricing lines. The --import-prices hint in the US3 "too old" line now works.

Tests:
- The five-row example from the spec: 2 rows imported as final, 3 skipped, the existing price unchanged, and only the 2 recent days requested from the source.
- A bad row on line 4: the run fails, nothing is imported, no lookups are made, and the file is unchanged.
- Importing the same file again imports nothing and skips all 5 rows.
- A failed sync means no import and no lookups.
- A missing file is an error.
- Without the option, nothing is imported.

Additions beyond the task list:
- Two file-reading tests: a file starting with a BOM is accepted, and a file that isn't valid UTF-8 is rejected with a clear error.
- Two error rules I chose:
  - A missing or wrong header reports no line number, matching the contract's …: header must be "date_utc,usd_price".
  - A row with only a date counts as "missing price" rather than a column-count error.
  - 
Phase 7 remains (T039–T043):
- the "transfer" wording scan;
- the API-key secrecy test;
- README updates;
- the final gate run;
- the manual check against CoinGecko, which you'll need to run.

## Notes
All gates pass a manual run.
All code passes a quick visual inspection.
