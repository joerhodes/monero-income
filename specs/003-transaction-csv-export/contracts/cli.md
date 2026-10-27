# Contract: command-line changes for feature 003

Additions to [feature 001's](../../001-sync-incoming-transactions/contracts/cli.md) and
[feature 002's](../../002-usd-valuation/contracts/cli.md) CLI contracts. Their rules still
apply: no traceback, no secrets, and "transaction(s)", never "transfer(s)".

## New option

```text
monero-income [--rpc-url URL] [--username NAME] [--db-path PATH] [--reports-path DIR]
              [--import-prices CSV]
              [--coingecko-api-key KEY] [--coingecko-api-key-type demo|pro]
```

| Option | Config key | Meaning |
|--------|-----------|---------|
| `--reports-path DIR` | `reports_path` | Directory for `xmr_income.csv`; overrides the config file ([config.md](config.md)) |

## Output

Standard output: after all of feature 002's lines, every successful run prints exactly one more
line, always last:

| Count | Line |
|-------|------|
| 1 | `Exported 1 transaction to <absolute path>.` |
| N ≠ 1 (including 0) | `Exported N transactions to <absolute path>.` |

`<absolute path>` is the export file's full path, for example `/Users/you/reports/xmr_income.csv`.
`N` is written without thousands separators. A run that fails never prints this line (FR-021).

## Exit status

Unchanged from features 001 and 002, plus one new **exit 1** case. When the sync and pricing
succeeded but the export can't be written (FR-008):

```text
Error: cannot write export <absolute path>: <reason>. Recorded transactions and prices were kept; the previous export was not changed.
```

`<reason>` is the operating system's message (for example `Permission denied`,
`No space left on device`, `Not a directory`). When the reports directory's filesystem
doesn't support file locking (FR-027), `<reason>` is exactly:

```text
the filesystem doesn't support file locking (some network shares don't); write the export to a local directory and copy it
``` The feature 001/002 lines for the sync and
pricing are **not** printed in this case, matching every other failure.

Ctrl-C during the write exits **130** with feature 001's
`Error: interrupted; anything already recorded was kept`. The previous export is unchanged.
