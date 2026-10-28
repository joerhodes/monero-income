# 45 - Implement Phase 6 of Income Summaries Feature

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-28

## Prompt
/speckit-implement Feature 004 (income summaries), Phase 6 only. 
Stop after Phase 6 so I can review, run the gates, and commit.

## What Came Back
I've finished Phase 6 (T026–T033, marked [X]) and stopped there. The summaries' time zone now comes from --timezone, then the timezone key in the config file, then the machine's zone. An empty or unknown zone stops the run before anything is opened or synced. All five gates pass: 520 tests at 97.00% coverage, and ruff, mypy and lint-imports are clean. Nothing is committed.

The checklist requirements.md is 16/16 ✓ PASS. The optional /speckit-git-commit pre-hook was offered and not run.

Tests first (T026–T029). All of these failed before the implementation, either at import or because the timezone field didn't exist yet.
- tests/unit/test_settings.py:
  - Unset gives None.
  - The file value is used, and the option overrides it.
  - "" and "  " from either source give invalid timezone: must not be empty.
  - timezone = 5 gives invalid timezone in <path>: expected a string.
  - There's no unknown-key warning.
- tests/adapters/test_timezones.py (new):
  - America/New_York and UTC load.
  - These are rejected, each with the name as the message: Mars/Olympus_Mons, America, america/new_york, ../etc/passwd and /etc/passwd.
- tests/integration/test_summary_timezone.py (new):
  - With the machine set to UTC, the 2026-11-01T03:30Z transaction lands in 2026-11 with no setting, in 2026-10 with the file set to New York, and in 2026-11 with the file set and --timezone UTC given.
  - Mars/Olympus_Mons fails with the contract's exact message before the wallet is created, and no database or export is created.
  - The configured zone also decides "today".
- tests/cli/test_cli_success.py: --timezone Europe/Berlin maps onto CliOptions, and leaving it out gives None.

Implementation (T030–T033):
- primitives/errors.py and new primitives/timezones.py: UnknownTimeZoneError, and load_zone(). It accepts only names in zoneinfo.available_timezones(), so a wrong-case name or a path is rejected even on macOS's case-insensitive file system.
- orchestration/settings.py: the timezone key on CliOptions and Settings, with the same empty check as reports_path and no zone loading.
- orchestration/run.py: the zone is loaded right after the settings are resolved, before connect. This replaces the temporary zone = None from Phase 3.
- cli.py: --timezone, after --reports-path, with the help text from the task. It shows in --help.

Beyond the task list:
- Extra test: the task's tests left the fallback in load_zone untested. That's the case where a listed name still fails to load, for example with a damaged database. I added one test for it, so timezones.py is at 100%.
- Fixes: a ruff import-sort fix, and patching zoneinfo directly in that test because mypy rejected reaching it through the timezones module.

## Notes
Reviewed all updated files.  No changes needed.
Ran gates manually.  All passed.
