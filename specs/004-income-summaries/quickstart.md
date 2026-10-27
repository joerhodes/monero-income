# Quickstart: validating the income summaries

**Feature**: 004-income-summaries

## Automated

```sh
uv run ruff check && uv run ruff format --check
uv run mypy
uv run lint-imports
uv run pytest            # includes the golden files tests/golden/summaries_*.txt
```

All gates must pass (constitution VII). The golden files are the reference for the format in
[contracts/summaries.md](contracts/summaries.md). Feature 003's export golden files must still
pass unchanged.

FR-018's safeguard is covered only by the automated tests in
`tests/integration/test_summary_failures.py` and `tests/cli/`. They inject a failure at each
stage: reading, unexpected data, computing, and rendering (research R10). It can't be
triggered by hand against a healthy database.

## By hand, against a real wallet

Prerequisites: features 001–003 set up (wallet RPC running, config file in place).

| # | Do | Expect |
|---|----|--------|
| 1 | `monero-income` in a wide terminal (at least 110 columns) | After `Exported …`, a blank line, then weekly on the left, monthly above annual on the right, in rounded boxes with bold headers |
| 2 | `COLUMNS=60 monero-income` | Weekly, then monthly, then annual, one after another |
| 3 | `monero-income \| cat` and `monero-income > /tmp/out.txt` | One after another, whatever the terminal width; `grep -c $'\x1b' /tmp/out.txt` is `0` (no ANSI codes in redirected output) |
| 4 | Count the rows | 26 weekly rows ending with this week's `YYYY-Www`, 12 monthly ending with this month, 4 annual ending with this year, each followed by `Total` |
| 5 | Pick a month and sum its rows in the export: `awk -F, '$3 ~ /^2026-10/ {x+=$4} END {print x}' ~/reports/xmr_income.csv` | Matches that month's XMR, give or take transactions near midnight that fall in a different month in local time (UTC export, local summaries) |
| 6 | If a day is still provisional (a payout today) | Its week, month, year, and the totals carry `*`; the legend explains `*` |
| 7 | `monero-income --timezone UTC`, then `--timezone Pacific/Kiritimati` | A transaction near midnight moves between periods; figures are otherwise unchanged |
| 8 | `monero-income --timezone Mars/Olympus_Mons` | `Error: invalid timezone: unknown time zone 'Mars/Olympus_Mons'`, exit 1; no sync line, export unchanged |
| 9 | Put `timezone = "America/New_York"` in the config file, then run with `--timezone UTC` | The option wins (US4-3) |
| 10 | `monero-income --db-path /tmp/empty-test.db` against a wallet with no incoming transactions (or a fresh test wallet) | `No transactions to summarize yet.` after the export line |
| 11 | Stop the wallet RPC; `monero-income` | Sync error, exit 1; no summaries |
