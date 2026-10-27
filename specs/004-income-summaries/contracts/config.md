# Contract: config key added by feature 004

Added to [feature 001's config file](../../001-sync-incoming-transactions/contracts/config.md)
and to the keys from features [002](../../002-usd-valuation/contracts/config.md) and
[003](../../003-transaction-csv-export/contracts/config.md). Their rules (precedence, missing
file, permissions warning, unknown-key warning) are unchanged.

```toml
timezone = "America/New_York"   # string, optional; default: the machine's local time zone
```

| Key | Type | Default | CLI override | Validation |
|-----|------|---------|--------------|------------|
| `timezone` | string | The machine's local time zone | `--timezone` | See below. Every error exits 1 before syncing (FR-006) |

The `timezone` key is validated in this order:

1. If the file's value isn't a string: `invalid timezone in <config path>: expected a string`.
2. If the value from the option or the file is empty or blank:
   `invalid timezone: must not be empty`. This is checked before the default applies, so
   `""` is an error, not the machine's zone.
3. If the name isn't in the system's time zone database (case-sensitive):
   `invalid timezone: unknown time zone '<name>'`. The name isn't secret, so it is echoed.

- **Names**: IANA time zone names, as listed by the system's time zone database, for example
  `America/New_York`, `Europe/Berlin`, or `UTC`.
- **Effect**: decides each transaction's period and the current period in the summaries
  ([summaries.md](summaries.md)). It doesn't change the export, which is in UTC, or which
  day's price a transaction is valued at, which is its UTC day.
