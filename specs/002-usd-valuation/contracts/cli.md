# Contract: command-line changes for feature 002

These are additions to [feature 001's CLI contract](../../001-sync-incoming-transactions/contracts/cli.md),
whose rules still apply: no traceback, no secrets, and "transaction(s)", never "transfer(s)".

## New option

```text
monero-income [--rpc-url URL] [--username NAME] [--db-path PATH] [--import-prices CSV]
              [--coingecko-api-key KEY] [--coingecko-api-key-type demo|pro]
```

| Option | Config key | Meaning |
|--------|-----------|---------|
| `--import-prices CSV` | none | Import daily prices from a CSV file after the sync, then continue as normal ([import-csv.md](import-csv.md)) |
| `--coingecko-api-key KEY` | `coingecko_api_key` | Price source API key; overrides the config file. Never shown in output. The config file is recommended, since a command-line key can end up in shell history |
| `--coingecko-api-key-type demo\|pro` | `coingecko_api_key_type` | Key type, which selects the header (and the default base URL); overrides the config file |

## Output

Standard output, after feature 001's sync line, in this order. Each line appears only when
its count is non-zero, except the last.

| Line | When |
|------|------|
| `Imported N prices; skipped M rows.` | `--import-prices` was given |
| `Priced N days (M provisional).` | N > 0 (omit ` (M provisional)` when M = 0) |
| `N days still have no price; a later run will try again.` | `no_price` > 0 |
| `N provisional prices couldn't be refreshed; a later run will try again.` | `not_refreshed` > 0 |
| `N days are older than the price history and can't be looked up; use --import-prices to add them.` | `too_old` > 0 |
| `All transactions are valued.` | at least one transaction is recorded and every day with transactions has a final price (FR-014); never printed for an empty database |

Use "day"/"price" and "row" singular when the count is 1.

Standard error, when pricing stopped early (the run continues and exits 0):

| Reason | Line |
|--------|------|
| Rate limited | `Warning: price lookups stopped: the price source is rate-limiting requests` |
| Key rejected | `Warning: price lookups stopped: the price source rejected the API key` |
| Unavailable | `Warning: price lookups stopped: cannot reach the price source: <reason>` |

## Exit status

These are unchanged from feature 001. Price-source problems exit **0** (FR-009). These exit
**1** with an `Error:` line:

- a storage error during pricing or import (FR-025): `Error: cannot write to database …`;
- an invalid import file (FR-020): `Error: cannot import prices from <path>: line N: <reason>`,
  or `…: <header or file problem>`;
- an invalid new config key: `Error: invalid <key>: <reason>`.
