# 14 - Implement Phase 6 - Final Polish

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-16

## Prompt
/speckit-implement Phase 6 only. In README.md, add the usage section
without changing the existing Intro or Status sections. Stop after
Phase 6 so I can review, run the gates, and commit.

## What Came Back
Phase 6 is done except T050, which I couldn't run: it needs monero-wallet-rpc, and it isn't 
installed on this machine. T047–T049 are marked [X] in tasks.md, T050 is still [ ], and nothing is committed.

┌──────────────────────────────────┬────────────────────────────┐
│               Gate               │           Result           │
├──────────────────────────────────┼────────────────────────────┤
│ ruff check / ruff format --check │ pass                       │
├──────────────────────────────────┼────────────────────────────┤
│ mypy (strict)                    │ no issues in 44 files      │
├──────────────────────────────────┼────────────────────────────┤
│ lint-imports                     │ 2 contracts kept           │
├──────────────────────────────────┼────────────────────────────┤
│ pytest                           │ 122 passed, coverage 94.5% │
└──────────────────────────────────┴────────────────────────────┘

- T047: tests/cli/test_messages.py checks every string literal in cli.py and orchestration/ and fails if any contains "transfer". It also checks that the scan really covers the CLI, run, settings and sync modules. I confirmed separately that it flags a literal like "two transfers". wallet.get_transfers(...) in sync.py is a method name, not a string, so it doesn't trip the test.
- T048: README.md has a new Usage section after Status, covering:
  - installing with uv;
  - the config file keys, chmod 600, and the password and rpc_url rules;
  - the command and its options;
  - the two possible output lines;
  - safe re-runs and resuming after an interruption;
  - error output and exit codes.

  As you asked, Intro and Status are unchanged, so Status still says "Not yet usable." T048 itself also said to update Status; I didn't, and you'll want to edit that line yourself before release.
- T049: all five gates pass, as in the table above.

One thing in the README I haven't tried: the uv tool install . line. I didn't run it because it installs the command into your user environment. The uv sync / uv run monero-income route is the one verified throughout implementation.

To finish T050, run quickstart §3 against a stagenet monero-wallet-rpc:
- first run and repeat run;
- comparing totals with sqlite3;
- wrong password;
- wallet stopped;
- Ctrl-C mid-run;
- loose config file permissions;
- a damaged database file.

The task says to record the results in the PR description, then mark T050 [X]. Don't commit any database or wallet files; .gitignore already covers *.db and config.toml.

## Notes
All gates run cleanly.
All code and tests pass an initial sniff test - nothing jumps out.

Ran a sync against wallet RPC and compared to previous version.
- Sync recorded the current number of transaction records.
- Last 5 transaction records match records from old system.
