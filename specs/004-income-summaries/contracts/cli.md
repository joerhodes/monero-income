# Contract: command-line changes for feature 004

Additions to the CLI contracts of features
[001](../../001-sync-incoming-transactions/contracts/cli.md),
[002](../../002-usd-valuation/contracts/cli.md) and
[003](../../003-transaction-csv-export/contracts/cli.md). Their rules still apply: no
traceback, no secrets, and "transaction(s)", never "transfer(s)".

## New option

```text
monero-income [--rpc-url URL] [--username NAME] [--db-path PATH] [--reports-path DIR]
              [--timezone ZONE]
              [--import-prices CSV]
              [--coingecko-api-key KEY] [--coingecko-api-key-type demo|pro]
```

| Option | Config key | Meaning |
|--------|-----------|---------|
| `--timezone ZONE` | `timezone` | IANA time zone for the summaries' periods. Overrides the config file ([config.md](config.md)) |

Help text: `Time zone for the income summaries, e.g. America/New_York (default: this machine's).`

## Output

Standard output for a successful run:

1. Features 001–003's lines, unchanged, ending with the `Exported …` line.
2. A blank line.
3. The summaries and the legend, or the no-transactions message ([summaries.md](summaries.md)).

- **Layout**: when standard output is a terminal, the CLI reads the terminal's width and the
  renderer chooses between the layouts. When it isn't (redirected to a file or a pipe), the
  summaries are always printed one after another.
- **Failed runs**: a run that fails before the export prints none of this, as before. A run
  whose summary step fails prints step 1 only, then the error (see Exit status).

## Exit status

Unchanged from features 001–003, plus two new **exit 1** cases.

**An invalid time zone setting** exits before syncing, with one of the
[config.md](config.md) messages:

```text
Error: invalid timezone: unknown time zone 'Mars/Olympus_Mons'
```

**The summaries can't be produced** (FR-018, research R10). This covers a failure in reading
the summary records, unexpected data, computing the summaries, or rendering them, after the
export was written. Standard output holds features 001–003's lines, including the
`Exported …` line, and nothing after them: no blank line and no partial summary. Standard
error holds any warnings, as before, then:

```text
Error: cannot show the income summaries: <reason>. The export was written to <absolute path>; recorded transactions and prices were kept.
```

| Failure | `<reason>` |
|---------|------------|
| Reading the summary records (`StorageReadError`) | `cannot read database <db path>: <error>` |
| Unexpected data in the records or in what was built (`SummaryDataError`) | Its message, e.g. `unexpected data for transaction <txid>: invalid price` |
| Anything else | `unexpected <ExceptionType>: <error>` |

The export on disk is the one this run wrote. The CLI builds the complete summary lines
before printing any line, so a rendering failure never leaves part of a table on screen.

A failure in the export's own read (for example, an unparseable stored price) still happens
before the export is written. It is feature 001's `Error: cannot read database …`, with no
lines printed and no export written, as in feature 003.

Ctrl-C during the summary step exits **130** with feature 001's
`Error: interrupted; anything already recorded was kept` and prints no lines.
