# Behaviors — USD Pricing (legacy)

Observed behavior of legacy `xmr-income-report` @ `54e77b9`. Describes what the old tool does, not what the rewrite should do.
Citations are `path:line` in the legacy repo. (inferred) = not read directly from code.

## Normal behavior

Each transaction is valued at the USD price for its UTC calendar day. (`src/xmr_income_report/report.py:102`, `:109`; `src/monero_tools/db.py:227`)

All transactions on the same UTC day share one price, looked up once. (`src/monero_tools/db.py:191`; `src/xmr_income_report/report.py:188`)

Each run looks up prices only for UTC days that have a recorded transaction and no price yet. (`src/monero_tools/db.py:179-193`; `src/xmr_income_report/report.py:182-184`)

Pricing runs on every run, after the sync, even when the sync found nothing new. (`src/xmr_income_report/cli.py:85-86`)

Once a day has a price, that price is never looked up again or changed. (`src/monero_tools/db.py:156`; `src/xmr_income_report/report.py:199`)

Each price is kept as soon as it is retrieved, so an interrupted run keeps the prices it already found. (`src/xmr_income_report/report.py:199`; `src/monero_tools/db.py:157`)

After pricing, the run displays "Fetched N new prices.", where N is the number of days priced this run, including 0. (`src/xmr_income_report/cli.py:158`)

A transaction's USD value is its XMR amount times its day's price, kept unrounded until output. (`src/xmr_income_report/report.py:237`)

On output, USD values are rounded to the nearest cent, with half-cents rounded away from zero. (`src/xmr_income_report/report.py:262-263`)

The price is kept at the precision the price source returns. (`src/monero_tools/coingecko.py:87`)

Price lookups are at least 1.2 seconds apart by default; the gap can be changed in the settings file. (`src/monero_tools/coingecko.py:70-73`; `src/xmr_income_report/report.py:91`)

The price source, coin, and API key can be set by option or settings file; the key is sent only when one is set. (`src/xmr_income_report/cli.py:52-56`; `src/xmr_income_report/report.py:87-90`; `src/monero_tools/coingecko.py:64`)

The report start date (`--since`) does not limit pricing; every recorded day without a price is looked up. (`src/xmr_income_report/cli.py:86-87`; `src/monero_tools/db.py:179-193`)

Days are looked up in no guaranteed order. (inferred: no ordering in `src/monero_tools/db.py:190-192`)

## Errors and edge cases

When the price source rate-limits a lookup, the tool waits 1, 2, 4, 8, then 16 seconds between up to five attempts for that day. (`src/monero_tools/coingecko.py:68-81`)

When a day cannot be priced (rate limit not cleared after five attempts, network failure, server error, or no price for that day), that day stays unpriced and the run continues with the remaining days. (`src/xmr_income_report/report.py:200-201`; `src/monero_tools/coingecko.py:83`, `:86-97`)

A rate-limited day does not stop or slow lookups for later days beyond the normal gap; each later day gets its own five attempts. (`src/xmr_income_report/report.py:188-201`)

Server errors other than rate limiting are not retried. (`src/monero_tools/coingecko.py:83`)

Unpriced days are retried automatically on the next run. (`src/xmr_income_report/report.py:174-177`)

When some days could not be priced, the run ends with "Failed to fetch prices for N transaction dates.", printed after the summaries. N counts days, not transactions. (`src/xmr_income_report/cli.py:190-193`)

Failing to price some days does not change the exit status; the run still succeeds. (`src/xmr_income_report/cli.py:144-163`, `:80-89`)

"Fetched N new prices." is shown even when some days failed. (`src/xmr_income_report/cli.py:158`)

An unexpected pricing error shows "Error looking up USD prices: <detail>", exits with status 1, and writes no files or summaries. Prices found before the error are kept. (`src/xmr_income_report/cli.py:159-161`, `:86-89`; `src/xmr_income_report/report.py:199`)

A transaction without a price has no USD value, not a value of zero, in the transaction list. (`src/xmr_income_report/report.py:236-237`) See behaviors-csv.md for how it appears.

A transaction without a price adds nothing to USD totals, but its XMR still counts. (`src/xmr_income_report/report.py:283`, `:323-326`)

Today's UTC price is looked up once and never refreshed. (`src/monero_tools/db.py:156`) The source returns the price at the start of that UTC day (inferred, external API behavior).

With the free public price source, days more than about a year old may never be priced. (inferred, external API limit)
