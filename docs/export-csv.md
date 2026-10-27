# The transaction export: `xmr_income.csv`

This document describes the CSV file that `monero-income` writes. It is written for someone
who has never used the tool, such as an accountant or auditor who receives the file. You
don't need to read anything else to understand the export.

## What the file is

`xmr_income.csv` lists every incoming Monero (XMR) transaction the tool has recorded for the
wallet, with the US dollar (USD) price of XMR on that transaction's day and the transaction's
USD value.

- **When it's written**: at the end of every successful run of the tool. A run succeeds even
  when some days couldn't be priced yet; those rows show `TBD` (see below).
- **Replaced in full**: each run writes the whole file again from everything recorded so far.
  The file is never appended to, and it is never left half-written: it is either the previous
  run's complete file or the new run's complete file.
- **Not written by a failed run**: if a run fails, the previous export is left exactly as it
  was.
- **Where**: in the reports directory, `~/reports` unless the user chose another directory.
- **Permissions**: only the file's owner can read or write it.

## Layout

- Plain text, UTF-8, comma-separated. Every value is ASCII and no value is ever quoted.
- Every line, including the last, ends with a line feed.
- The first line is the header:

  ```text
  txid,height,timestamp_utc,xmr,usd_price,price_status,usd_value
  ```

- Then **one row per incoming transaction**, oldest first: sorted by `timestamp_utc`, then by
  `height`, then by `txid`. With no transactions, the file is just the header.

Block timestamps don't always increase with block height, so a row can have a lower `height`
than the row before it. The order is by time first.

## Columns

| # | Column | Meaning | Format and units |
|---|--------|---------|------------------|
| 1 | `txid` | The transaction id on the Monero blockchain | 64 lowercase hexadecimal characters |
| 2 | `height` | The block the transaction was included in | Whole number, no separators |
| 3 | `timestamp_utc` | When the transaction happened, in UTC | `YYYY-MM-DDTHH:MM:SSZ`, for example `2026-10-17T14:03:05Z` |
| 4 | `xmr` | The amount received, in XMR | Digits, a `.`, then exactly 12 decimal places, for example `1.234567890123`. This is the exact amount: XMR's smallest unit is 0.000000000001 XMR |
| 5 | `usd_price` | The USD price of 1 XMR on the transaction's UTC day | A plain decimal number with as many decimal places as were recorded, for example `152.3456`, `150`, or `163.40000000000001`; or `TBD` |
| 6 | `price_status` | Whether that price can still change | `final`, `provisional`, or `TBD` |
| 7 | `usd_value` | The transaction's value in USD: `xmr × usd_price`, rounded to the cent | Digits, a `.`, then exactly 2 decimal places, for example `188.08`; or `TBD` |

`usd_price`, `price_status` and `usd_value` are either all `TBD` or none of them are.

## Price status: `final`, `provisional`, `TBD`

- **`final`**: the day's price is settled and will never change in a later export.
- **`provisional`**: the day's price was recorded before the day was over, or shortly after.
  It may still be replaced by a later run until one hour after that UTC day ends. After that,
  the next run records the day's price as final. `usd_value` on a provisional row is computed
  from the provisional price, so it may change too.
- **`TBD`** (to be determined): no price has been recorded for that day yet, for any reason.
  For example, the price source couldn't be reached during the run, or the day is older than
  the price source's history and no price was supplied for it. A later export may fill it in.

Every row on the same UTC date has the same `usd_price` and `price_status`.

## Which day's price applies

Each transaction uses the price for the **UTC calendar date** of its `timestamp_utc`: the
`YYYY-MM-DD` part of that value. A transaction at `2026-10-19T00:00:00Z` uses the
2026-10-19 price, and one at `2026-10-18T23:59:59Z` uses the 2026-10-18 price, whatever the
local time was where the wallet's owner lives.

## Exact values and rounding

Every value in the file is exact except `usd_value`. `xmr` is the exact amount received and
`usd_price` is the exact price that was recorded, with no digits added or removed.

`usd_value` is the only rounded column. It is calculated from the exact `xmr` and the exact
`usd_price`, and only the result is rounded to the nearest cent. An exact half cent rounds up
(away from zero). For example:

```text
1.000000000000 × 152.345 = 152.345 → 152.35
```

Other examples from the sample below:

- `1.234567890123 × 152.3456 = 188.0809...` → `188.08`
- `0.500000000000 × 152.345 = 76.1725` → `76.17` (less than half a cent above 76.17)
- `0.000000000001 × 150 = 0.00000000015` → `0.00` (less than half a cent)
- `1234.500000000000 × 150 = 185175` → `185175.00`

To check a row, multiply `xmr` by `usd_price` with a calculator that keeps all the digits, and
round the result to two decimal places, rounding a half cent up.

No value is written in scientific notation (such as `1.5E-10`) or with thousands separators
(such as `185,175.00`).

## Opening the file in a spreadsheet

Spreadsheet programs may show fewer decimal places than the file holds, for example
`1.234567890123` as `1.234568`, or `163.40000000000001` as `163.4`. They may also drop
trailing zeros. The file itself is exact. When checking a value, look at the file's text, for
example by opening it in a text editor, or format the spreadsheet's cells as text before
importing.

## Where the export can be written

The reports directory must be on a filesystem that supports file locking. The tool uses a
lock so that two runs at the same time can't overwrite each other's export. Some network
shares don't support locking; there the run fails with a message saying so, and any export
already in that directory is left unchanged. To share the export on such a drive, write it to
a local directory and copy it.

## Example

This example has six transactions. The prices recorded were: 2026-10-17 final `152.3456`;
2026-10-18 final `152.345`; 2026-10-19 final `150`; 2026-10-25 provisional
`163.40000000000001`; and no price for 2026-10-20. The txids are placeholders; a real file has
64 hexadecimal characters in each.

```text
txid,height,timestamp_utc,xmr,usd_price,price_status,usd_value
<64 hex>,3530000,2026-10-17T14:03:05Z,1.234567890123,152.3456,final,188.08
<64 hex>,3530700,2026-10-18T09:12:44Z,1.000000000000,152.345,final,152.35
<64 hex>,3531400,2026-10-19T00:00:00Z,0.000000000001,150,final,0.00
<64 hex>,3531450,2026-10-19T02:30:00Z,1234.500000000000,150,final,185175.00
<64 hex>,3532100,2026-10-20T18:45:10Z,0.731000000000,TBD,TBD,TBD
<64 hex>,3539000,2026-10-25T11:00:00Z,2.000000000000,163.40000000000001,provisional,326.80
```

- Row 1: an ordinary final price; `188.0809...` rounds to `188.08`.
- Row 2: exactly half a cent (`152.345`), which rounds up to `152.35`.
- Row 3: the smallest possible amount. Its exact value, 0.00000000015 USD, rounds to `0.00`.
- Row 4: a whole-number price, written `150` with no decimal places because that is how it was
  recorded.
- Row 5: no price was recorded for 2026-10-20, so the last three columns are `TBD`.
- Row 6: a provisional price recorded with many decimal places, written in full;
  `2 × 163.40000000000001 = 326.80000000000002` rounds to `326.80`.

## What the file doesn't include

The export doesn't say where a price came from (looked up online or supplied by the user) or
when it was recorded.
