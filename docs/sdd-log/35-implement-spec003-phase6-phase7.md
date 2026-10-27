# 35 - Implmement spec 003, phase 6 and phase 7

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-27

## Prompt
/speckit-implement Phase 6 and Phase 7 only.  Stop after
phase 7 so I can review, run the gates, and commit.

## What Came Back
Phases 6 and 7 are done except T034

All five gates pass: ruff check, ruff format, mypy, lint-imports (2 contracts kept), and pytest (393 passed, 96.29% coverage). Nothing is committed.

Phase 6 (US4: reader documentation)
- T028: New file docs/export-csv.md, written for someone who has never seen the tool. It covers every item on the task's list. To check the worked examples, I recomputed them with Decimal. Row 1's exact value is 188.0809…, which I had first written wrongly and then fixed.
- T029: Updated the Usage section of README.md:
  - added reports_path to the config example
  - added --reports-path DIR to the usage line
  - added the Exported N transactions to … line as the last line of the output example
  - added a new "The export" subsection with the permissions, the replace-in-full behavior, the file-locking note and the link to the new doc

  One change goes beyond the task: I kept a clause about the CSV export ahead of the new "Summaries come in a later feature." sentence. If you want only that sentence, trim the clause. The Intro, Status and "How I used AI" sections are unchanged.
- T030: I checked the doc against the golden file. Every value form in it is explained in the doc, and the doc's example rows are the contract's example word for word. The doc also explains the golden file's extra 76.17 row (76.1725).

Phase 7 (polish)
- T031: The glob in tests/cli/test_messages.py (orchestration/*.py plus cli.py) covers export.py and export_format.py. No new text says "transfer", and the export and error messages say "transaction(s)".
- T032: Added test_rows_parse_back_to_the_recorded_values to tests/unit/test_export_format.py. It generates 300 records with a seeded random.Random and makes the four checks from the task, including comparing the usd_price text exactly. No new dependency was added.
- T033: I ran the gates and fixed two problems in my new test: a docstring line that was too long and one formatting issue.
- T034 (not done): The quickstart manual checks need your real wallet, so I left this unchecked. Record the results in the PR description.

Changed files: README.md, docs/export-csv.md (new), tests/unit/test_export_format.py, specs/003-transaction-csv-export/tasks.md. There is also an untracked file, docs/sdd-log/35-…md, which is yours; I didn't touch it.

## Notes
All gates passed on a manual run
All changes reviewed
Ran against real wallet.  Export CSV transaction file is good.
