# 31 - Implement Spec 003, Phase 1 and Phase 2

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-26

## Prompt
/speckit-implement Phase 1 (Setup) and Phase 2 (Foundational) only. Stop
after Phase 2 so I can review, run the gates, and commit.

## What Came Back
I've finished Phase 1 and Phase 2 (T001–T006), marked those tasks [X] in tasks.md, and stopped there as you asked. Nothing is committed.

The five gates passed before I changed anything (300 tests, 95.70% coverage). After my changes they still pass: ruff check, ruff format, mypy --strict and import-linter are clean, and pytest shows 308 passed with 95.72% coverage.

What changed
- T002 (src/monero_income/primitives/errors.py): added ExportWriteError and ExportLockUnsupportedError. The second is a subclass of the first and always carries the fixed message from contracts/cli.md.
- T003 (src/monero_income/primitives/models.py): added ExportRecord, a frozen dataclass with the six fields and comments from the task.
- T004 (src/monero_income/orchestration/settings.py): added the reports_path setting, defaulting to ~/reports.
  - It's added to STRING_KEYS, CliOptions and Settings.
  - An empty or blank value from the option or the config file is rejected before the default applies, so "" is an error rather than silently becoming the default.
  - db_path's code is unchanged.
- T005 (tests/unit/test_settings.py): six new tests cover the default under HOME, the config-file value, ~ expansion, the option overriding the file, "" and "  " from either source, a non-string value, and no unknown-key warning. I also added reports_path to the existing wrong-type test.
- T006: added ExportSummary in the new src/monero_income/orchestration/export.py, added RunResult.exported (default None) in run.py, and re-exported ExportSummary from orchestration/__init__.py.

I also edited one existing test, test_defaults_apply_without_options_or_file, to expect reports_path=<HOME>/reports. It compares the whole Settings object, so the new field would otherwise have failed it.

One thing you might notice on review: ExportLockUnsupportedError.__init__ isn't covered by any test yet. T020 in Phase 4 tests it.

## Notes
All gates passed a manual run.
Code updates look clean
