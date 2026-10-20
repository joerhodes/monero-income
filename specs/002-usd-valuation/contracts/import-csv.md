# Contract: price import CSV (`--import-prices`, P3)

```csv
date_utc,usd_price
2024-03-01,151.234
2024-03-02,149.9
```

- **Encoding**: UTF-8; a leading BOM is allowed. **Header**: exactly `date_utc,usd_price`, in
  this order, with surrounding whitespace trimmed. Extra columns are an error.
- `date_utc`: `YYYY-MM-DD`, a real calendar date.
- `usd_price`: USD per 1 XMR, matching `^[0-9]+(\.[0-9]+)?$` and greater than 0. Stored exactly
  as given (canonical decimal text).
- Blank lines are ignored. A date may appear only once.

## Processing (FR-019, FR-020)

1. Read the whole file (primitives, I/O only).
2. `parse_import(text)` (pure) validates **every** row before anything is written. The first
   problem rejects the file:
   `cannot import prices from <path>: line <n>: <reason>` (`bad date "2024-13-01"`,
   `missing price`, `price must be greater than 0`, `date 2024-03-01 already on line 4`),
   or `…: header must be "date_utc,usd_price"`, or `…: <OS error>`.
3. `select_imports` keeps rows with `date_utc < history_cutoff(today)` and no recorded price
   (provisional or final). All other rows are counted as `skipped`.
4. The kept rows are inserted in **one transaction** with `status = 'final'`,
   `source = 'import'`, and `fetched_at = now`.
5. The run then continues with price lookups. Imported days are no longer needs, so they
   aren't requested.

The import runs only after a successful sync, and never runs without the option.
