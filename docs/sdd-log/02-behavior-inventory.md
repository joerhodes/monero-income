# 02 - Behavior Inventory

This list of behaviors from the previous `xmr-income-report` will
inform the list of specs to create.

## Summary

Each application run does:

1. Retrieves new incoming transactions from wallet.
2. Look up USD pricing for new transactions.
3. Save all recorded transactions and monthly summaries to CSV files.
4. Display weekly and monthly summaries to screen.

These are detailed below.

## Retrieve new incoming transactions from wallet (sync)

Running a sync records every incoming wallet transactions that aren't already recorded.

Running a sync again with no new transactions changes nothing.

If a sync is interrupted, already recorded transactions are kept, 
and the next sync records the rest.

Outgoing transactions are not recorded.

Any error encountered during the sync is reported to the user, and the application exits.

If no new transactions are found during the sync, a message is displayed to the user before continuing.

Each recorded transaction keeps the exact moment it occurred, independent of time zone.

## Look up USD pricing for new transactions

USD amounts are kept at full precision; rounding to $0.01 happens only on output. Monthly and weekly totals are summed at full precision and rounded once.

Each transaction is valued at the USD price for its UTC calendar day.

Running a sync looks up the USD value for every recorded transaction that doesn't have a USD value yet.

If the look up is interrupted, USD values already assigned are kept, and the next run updates the rest.

If the price source is unavailable or rate-limits the run, USD values already assigned are kept, 
the run reports how many transactions remain unvalued, and the next run continues.

## Save all recorded transactions and monthly summaries to CSV files.

All dates and times are converted to the time zone of the machine running the tool only when output. 
Grouping by week and month uses that local time zone. USD prices always use the transaction's UTC 
calendar day, which may differ from its local date.

Each run creates or overwrites a CSV file with a list of all transactions, and any transactions 
without a USD value are recorded with an empty value.

A transaction without a USD value has no value, not a value of zero. It appears with an empty USD 
value in the transaction CSV, and contributes nothing to USD totals in the monthly and weekly summaries.  
Its XMR amount is still included in the monthly and weekly summaries.

| Column | Meaning |
|---|---|
| date_local | Date of the transaction in the local time zone, YYYY-MM-DD |
| time_local | Time of the transaction in the local time zone, HH:MM:SS |
| txid | The Monero transaction id |
| height | Block chain height of the transaction |
| xmr | Amount of the Monero transaction with full precision |
| usd_price | USD Price for 1.0 Monero for the transaction's UTC calendar day with full precision |
| usd_value | USD valuation for this transaction, rounded to the nearest $0.01 |
| iso_week_local | The ISO week number for the transaction in the local time zone, YYYY-WNN |
| month_local | The year and month of the transaction, YYYY-MM |
| year_local | The year of the transaction, YYYY |

Each run creates or overwrites a CSV file of the monthly summary of transactions, and transactions without a USD value are treated as 0 valued.

| Column | Meaning |
|---|---|
| month | YYYY-MM |
| xmr | sum of transactions for the month |
| usd_value | sum of the USD value for the month |

Each run overwrites the previous files.

Summaries cover every week and month from the first recorded transaction to the present.

## Display weekly and monthly summaries to screen.

Each run prints a list of weekly transaction summaries.

Each run prints a list monthly transaction summaries.
