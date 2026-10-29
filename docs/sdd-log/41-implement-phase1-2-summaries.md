# 41 - Implement Phase 1 and Phase 2 for Income Summaries Feature

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-28

## Prompt
/speckit-implement Feature 004 (income summaries), Phase 1 and Phase 2
only. Stop after Phase 2 so I can review, run the gates, and commit.

## What Came Back
Phases 1 and 2 are done (T001–T004 marked [X]), and I've stopped there. All five gates pass: 394 tests, 96.14% coverage. Nothing is committed.

Phase 1 (T001): before any change, uv sync and all five gates passed (393 tests). rich 15.0.0 is declared in pyproject.toml and locked in uv.lock.

Phase 2:
- T002, new src/monero_income/orchestration/summary.py: SummaryDataError, the frozen dataclasses PeriodFigures, Summary and IncomeSummaries, the title and range constants, and summary_failure_message. The task's one-line module docstring was 105 characters, over ruff's 100 limit, so I wrapped it onto two lines with the same words.
- T003, run.py:
  - RunResult gains summaries: IncomeSummaries | None = None.
  - New SummaryError(RunError) carries result.
  - The four new names are re-exported from orchestration/__init__.py.
  - Existing RunResult(...) calls are unchanged.
- T004, tests/conftest.py: the local_tz fixture, plus its one-line test in the new tests/unit/test_summary.py.
  - It uses its own pytest.MonkeyPatch.context() rather than the shared monkeypatch, so TZ is restored before the final time.tzset(). With the shared one, the final tzset() would run while TZ was still set.
  - The task says monkeypatch.setenv; this does the same thing on a private instance.

Also changed: the implement skill's ignore-file check added *.pyc, dist/ and *.egg-info/ to .gitignore. Revert that if you'd rather keep it out of this commit.

## Notes
Reviewed all file changes.  No additional updates needed.
All gates pass on a manual run.
Manually updated README to mark Income Summary feature as in progress
