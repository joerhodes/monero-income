# Contract: the transaction export file

The file `xmr_income.csv`, written by every successful run. This is report output under the
constitution: any change to it must be stated in a spec and update the golden files
(`tests/golden/`) in the same change.

## Location and permissions

- `<reports directory>/xmr_income.csv`. The directory comes from `--reports-path`, then the
  `reports_path` config key, then `~/reports` ([config.md](config.md)).
- Mode `0o600` after every write (FR-026).
- Replaced atomically; never partial (FR-007, [research R1–R3](../research.md)).

## Encoding

- UTF-8, no byte-order mark. Every value is ASCII.
- Comma-separated. No value is ever quoted: none contains a comma, quote, or line break.
- Every line, including the last, ends with `\n` (LF).

## Rows

1. Exactly one header line:

   ```text
   txid,height,timestamp_utc,xmr,usd_price,price_status,usd_value
   ```

2. Then one line per recorded transaction, sorted by `timestamp_utc`, then `height`, then
   `txid` (all ascending). No other lines; with no transactions the file is the header alone.

## Columns

| # | Column | Format | Source | Exact? |
|---|--------|--------|--------|--------|
| 1 | `txid` | 64 lowercase hex characters | Recorded transaction id | Yes |
| 2 | `height` | Decimal integer, no separators | Recorded block height | Yes |
| 3 | `timestamp_utc` | `YYYY-MM-DDTHH:MM:SSZ` | Recorded moment (UTC Unix seconds) | Yes |
| 4 | `xmr` | Digits, `.`, exactly 12 digits | Recorded amount in piconero ÷ 10¹² | Yes |
| 5 | `usd_price` | Plain decimal (no exponent, no separators, as many decimals as recorded), or `TBD` | Recorded price for the UTC date of `timestamp_utc` | Yes |
| 6 | `price_status` | `final`, `provisional`, or `TBD` | That price's status | Yes |
| 7 | `usd_value` | Digits, `.`, exactly 2 digits, or `TBD` | `xmr × usd_price`, rounded to the cent, half up | Rounded |

`usd_price`, `price_status` and `usd_value` are either all `TBD` or none are.

## Example

Prices recorded: 2026-10-17 final `152.3456`; 2026-10-18 final `152.345`; 2026-10-19 final
`150`; 2026-10-25 provisional `163.40000000000001`; 2026-10-20 none.

```text
txid,height,timestamp_utc,xmr,usd_price,price_status,usd_value
<64 hex>,3530000,2026-10-17T14:03:05Z,1.234567890123,152.3456,final,188.08
<64 hex>,3530700,2026-10-18T09:12:44Z,1.000000000000,152.345,final,152.35
<64 hex>,3531400,2026-10-19T00:00:00Z,0.000000000001,150,final,0.00
<64 hex>,3531450,2026-10-19T02:30:00Z,1234.500000000000,150,final,185175.00
<64 hex>,3532100,2026-10-20T18:45:10Z,0.731000000000,TBD,TBD,TBD
<64 hex>,3539000,2026-10-25T11:00:00Z,2.000000000000,163.40000000000001,provisional,326.80
```

Row 2 is a half cent (152.345 exactly) and rounds up. Row 3's exact value is
0.00000000015 USD.

## Rebuilding (FR-019)

From the export alone, without loss:

- **Each transaction**: `txid`, `height`, `occurred_at` = `timestamp_utc` as Unix seconds,
  `amount_piconero` = `xmr` × 10¹².
- **Each priced day**: date = the UTC date of `timestamp_utc`, price = `usd_price`, status =
  `price_status`. Every row on the same UTC date carries the same price and status.

Not included: where a price came from (lookup or import) and when it was fetched. Restoring
from the export is out of scope.
