# 46 - Implement Phase 7 for Income Summaries Feature

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-28

## Prompt
/speckit-implement Feature 004 (income summaries), Phase 7 only. 
Stop after Phase 7 so I can review, run the gates, and commit.

## What Came Back
I've done T035–T037 of Phase 7 and stopped. T038, the hand checks against your real wallet, is the only Phase 7 task left open, along with the README status row. All five gates pass: 520 tests at 97.00% coverage, and ruff, mypy and lint-imports are clean. Nothing is committed.

The checklist requirements.md is 16/16 ✓ PASS. The optional /speckit-git-commit pre-hook was offered and not run.

- T035: the "transfer" scan in tests/cli/test_messages.py already picks up summary.py and summary_format.py through its orchestration/*.py glob. I added both names to the test's coverage assertion so a rename can't quietly drop them. Every new message says "transaction(s)".
- T036, README.md:
  - The Usage intro now says every run ends with weekly, monthly and annual summaries.
  - The config example has timezone = "America/New_York"   # optional; default: this machine's time zone.
  - The usage block has [--timezone ZONE] after [--reports-path DIR].
  - The Run paragraph now says the summaries print last.
  - There's a new The summaries subsection. It covers the three ranges, ISO week labels, the time zone (prices stay by UTC day), the */? marks, the two layouts, the plain one-after-another output when redirected, an excerpt of the contract's annual table with the legend, and what a summary failure does.
  - I didn't touch the Intro or "How I used AI" sections.
- T037: all five gates passed with no fixes needed.

Decision for you: T036 asked me to replace a Planned row for 004 with [004 Income summaries](specs/004-income-summaries/) | In Progress | Weekly, monthly and annual summaries on screen. The row already says In Progress, with your own wording from commit 747fc62: "Income Summaries" / "Weekly, monthly and annual income tables". So I left it as it is. Say if you want the task's wording instead.

Still to do (T038): run the "By hand, against a real wallet" checks in specs/004-income-summaries/quickstart.md and record the results in the PR description. Don't commit any output, database or config file.

## Notes
Read all updates files.  Need to update feature status in README after manual testing.
Manually ran all gates.  All passed.

Ran `monero-income` against wallet.  All XMR values matched.  But USD values before 2026-W24 did not.
Reloading all pricing between February and June with the legacy tool to ensure that all pricing in 
this range is final. - This fixed the USD value discrepancy between the two reports.
So both reports now match.
