# Behaviors — CSV Output (legacy)

Observed behavior of legacy `xmr-income-report` @ `54e77b9`. Describes what the old tool does, not what the rewrite should do.
Citations are `path:line` in the legacy repo. (inferred) = not read directly from code. "verified" = confirmed by running the legacy functions on sample data.

## Files

Each successful run writes two files: `xmr_income.csv` (transactions) and `xmr_income_monthly.csv` (monthly summary). (`src/xmr_income_report/cli.py:121`)

Both files go in the output directory, which defaults to the directory the tool is run from. (`src/xmr_income_report/report.py:84`)

The output directory is created if it does not exist, including missing parent directories. (`src/xmr_income_report/cli.py:119-120`)

Each run fully replaces both files. (`src/xmr_income_report/report.py:268`, `:285`)

After writing, the run displays "Wrote <path>" for each file, transactions first. (`src/xmr_income_report/cli.py:173-174`)

The files are written before the on-screen summaries are shown. (`src/xmr_income_report/cli.py:88-89`)

When a run stops early with an error (invalid start date, sync error, pricing error), neither file is written and existing files are left as they were. (`src/xmr_income_report/cli.py:76`, `:85-88`)

Rows end with a carriage return and line feed. (inferred: Python `csv` default)

## Time zone and date range

Dates, times, weeks, months, and years use the configured time zone, which defaults to America/Chicago, not the machine's time zone. (`src/xmr_income_report/report.py:83`, `:231`)

A transaction's local date can differ from the UTC day used for its price. (`src/xmr_income_report/report.py:231`, `:109`; verified: 03:00 UTC on 2024-01-01 is listed as 2023-12-31 but priced for 2024-01-01)

With `--since`, only transactions on or after that date are written to either file. The date is compared in UTC, not local time. (`src/xmr_income_report/report.py:232-233`)

Because the start date is compared in UTC, a transaction whose local date is before the start date can appear. (verified: `--since 2024-01-01` kept a row dated 2023-12-31)

With `--since`, the files are replaced with the filtered subset; earlier rows from previous runs are not kept. (`src/xmr_income_report/report.py:268`, `:232-233`)

`--since` accepts any ISO 8601 date form, e.g. `2024-01-15`, `20240115`, or `2024-W03-1`. (`src/xmr_income_report/cli.py:99`; verified)

## Transaction file

The header is `date_local,time_local,txid,height,xmr,usd_price,usd_value,iso_week_local,month_local,year_local`. (`src/xmr_income_report/report.py:37-48`, `:270`)

There is one row per recorded transaction in range, oldest first by local date and time. (`src/xmr_income_report/report.py:253`)

Transactions with the same local date and time appear in no guaranteed order. (inferred: `src/xmr_income_report/report.py:253` has no tie-breaker; `src/monero_tools/db.py:222-229` has no ordering)

During the hour repeated when daylight saving time ends, rows are ordered by local clock time, not by when they occurred. (inferred: `src/xmr_income_report/report.py:253` sorts on local date and time)

`date_local` is `YYYY-MM-DD` and `time_local` is 24-hour `HH:MM:SS`. (`src/xmr_income_report/report.py:240-241`; verified)

`xmr` is the exact amount with no trailing zeros: `0.5`, `2` for whole amounts, and scientific notation for very small amounts, e.g. `1E-7`. (`src/xmr_income_report/report.py:107`, `:235`; verified)

`usd_price` is the day's price exactly as stored, e.g. `150.0`. It is empty when the day has no price. (`src/xmr_income_report/report.py:236`; verified)

`usd_value` is rounded to the nearest cent with two decimals, half-cents away from zero. It is `TBD` when the day has no price. (`src/xmr_income_report/report.py:262-263`, `:272`; verified)

`iso_week_local` is the ISO week as `YYYY-Www`; around New Year its year can differ from the calendar year, e.g. 2024-12-30 is `2025-W01`. (`src/monero_tools/date_utils.py:26-27`; `tests/monero_tools/test_date_utils.py:22-23`)

`month_local` is `YYYY-MM` and `year_local` is `YYYY`. (`src/monero_tools/date_utils.py:44`, `:61`)

With no transactions in range, the file has only the header. (`src/xmr_income_report/report.py:269-271`)

## Monthly file

The header is `month,xmr,usd_value`. (`src/xmr_income_report/report.py:286-287`)

There is one row per local month that has at least one transaction in range, oldest first. Months with no transactions are left out. (`src/xmr_income_report/report.py:278-288`)

`xmr` is the exact XMR total for the month, formatted like the transaction file's `xmr`. (`src/xmr_income_report/report.py:282`, `:292`)

`usd_value` is the month's unrounded USD total, rounded once to the nearest cent. It can differ by a few cents from adding the rounded values in the transaction file. (`src/xmr_income_report/report.py:283`, `:293`)

Transactions without a price add their XMR to the month but nothing to its USD total. A month with only unpriced transactions shows `0.00`. (`src/xmr_income_report/report.py:283`; verified)

With no transactions in range, the file has only the header. (`src/xmr_income_report/report.py:287-288`)

## Errors

An unknown time zone stops the run with an unformatted error after sync and pricing have finished; no files are written. (`src/xmr_income_report/report.py:227`; verified: `ZoneInfoNotFoundError`)

An output directory that cannot be created or written stops the run with an unformatted error after sync and pricing have finished. (inferred: `src/xmr_income_report/cli.py:119-120`, `src/xmr_income_report/report.py:268` are not wrapped in error handling)

If writing stops partway, a file can be left incomplete. (inferred: files are written in place, `src/xmr_income_report/report.py:268`, `:285`)
