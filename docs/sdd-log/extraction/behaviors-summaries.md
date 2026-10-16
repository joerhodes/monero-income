# Behaviors — On-Screen Summaries (legacy)

Observed behavior of legacy `xmr-income-report` @ `54e77b9`. Describes what the old tool does, not what the rewrite should do.
Citations are `path:line` in the legacy repo. (inferred) = not read directly from code.

## Normal behavior

Each successful run prints three tables, in order: "Weekly Summary", "Monthly Summary", "Yearly Summary". (`src/xmr_income_report/cli.py:184-188`)

A blank line comes before each table. (`src/xmr_income_report/cli.py:183`, `:185`, `:187`)

The tables follow the "Wrote <path>" lines for the CSV files. (`src/xmr_income_report/cli.py:88-89`, `:173-174`)

Each table has three columns: "Period", "XMR", "USD Value". (`src/xmr_income_report/cli.py:198-200`)

Each table has one row per period with at least one transaction in range, oldest first. Periods with no transactions are left out. (`src/xmr_income_report/cli.py:202`; `src/xmr_income_report/report.py:315-322`)

Periods use the configured time zone (America/Chicago by default), not the machine's. (`src/xmr_income_report/report.py:83`, `:231`, `:247-249`)

Weekly periods are ISO weeks shown as `YYYY-Www`; around New Year a week can carry the next or previous year, e.g. `2025-W01` for 2024-12-30. (`src/monero_tools/date_utils.py:26-27`)

Monthly periods are shown as `YYYY-MM` and yearly periods as `YYYY`. (`src/monero_tools/date_utils.py:44`, `:61`)

XMR totals are exact, with no trailing zeros; whole totals show without a decimal point, and very small totals use scientific notation. (`src/xmr_income_report/cli.py:206`; `src/xmr_income_report/report.py:323`)

USD totals show as `$` plus the amount rounded once to the nearest cent, half-cents away from zero. (`src/xmr_income_report/cli.py:207`; `src/xmr_income_report/report.py:262-263`, `:324-326`)

USD totals add unrounded transaction values and round once per period. (`src/xmr_income_report/report.py:324-326`)

Monthly figures on screen match the monthly CSV file. (`src/xmr_income_report/report.py:278-283` vs `:315-326`)

With `--since`, only transactions on or after that UTC date are summarized, so the first week or month may be partial. (`src/xmr_income_report/report.py:232-233`; `src/xmr_income_report/cli.py:87`)

Without `--since`, all recorded transactions are summarized. (`src/xmr_income_report/report.py:232`)

## Unpriced transactions

A transaction without a price adds its XMR to every period but nothing to USD. (`src/xmr_income_report/report.py:323-326`)

A period whose transactions are all unpriced shows `$0.00`. (`src/xmr_income_report/report.py:322`, `:324-326`)

The tables do not mark which periods include unpriced transactions. (`src/xmr_income_report/cli.py:202-208`)

When some days could not be priced, "Failed to fetch prices for N transaction dates." is printed after the Yearly Summary. (`src/xmr_income_report/cli.py:190-193`)

## Edge cases

With no transactions in range, each table prints with its title and headers and no rows. (inferred: empty loop at `src/xmr_income_report/cli.py:202`, `rich` renders header-only tables)

When the run stops early with an error, no tables are printed. (`src/xmr_income_report/cli.py:85-89`)

An unknown time zone stops the run before the tables. (`src/xmr_income_report/report.py:227`)

Table layout depends on terminal width; narrow terminals wrap or shorten cells. (inferred: `rich` table rendering, `src/xmr_income_report/cli.py:197`)

Headers are bold cyan and periods dim when the terminal supports color. (`src/xmr_income_report/cli.py:197-198`)
