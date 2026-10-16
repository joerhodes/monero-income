# Contract: `monero-income` command line

A single command with no subcommands. Every run begins with a sync (FR-001); in this
feature, the sync is the whole run.

## Synopsis

```text
monero-income [--rpc-url URL] [--username NAME] [--db-path PATH]
```

| Option | Config key | Meaning |
|--------|-----------|---------|
| `--rpc-url URL` | `rpc_url` | Wallet RPC address |
| `--username NAME` | `username` | Wallet RPC login name (enables HTTP Digest) |
| `--db-path PATH` | `db_path` | SQLite database file |

There is deliberately **no `--password` option**. The password is read from the config file
only. Option values override the config file (see [config.md](config.md)).

## Output

Standard output, exactly one line on success:

| Situation | Line |
|-----------|------|
| Nothing new | `No new transactions found.` |
| One new | `Recorded 1 new transaction.` |
| N > 1 new | `Recorded N new transactions.` |

Standard error:

- Warnings: `Warning: <message>`. The run continues. Example:
  `Warning: config file /home/u/.config/monero-income/config.toml is readable by other users; run chmod 600 on it.`
- Errors: `Error: <message>`. The run stops.

Rules that apply to every message:

- Never a traceback (FR-015).
- Never the password (FR-018).
- Says "transaction(s)", never "transfer(s)" (FR-019).
- Wallet addresses are shown as configured (they can't contain credentials, see config.md).

## Exit status

| Code | Meaning |
|------|---------|
| 0 | Sync completed (including "No new transactions found.") |
| 1 | Any error: invalid settings, config file unreadable, database unreadable or newer schema, database write failed, wallet unreachable, login rejected, wallet error, invalid wallet response, or an unexpected internal error |
| 2 | Command-line usage error (unknown option, missing option value), reported by Typer/Click without a traceback |
| 130 | Interrupted (Ctrl-C). Height windows committed before the interruption are kept. |

## Error message catalogue

Wording may be refined during implementation, but each error must identify its category as
listed here. Tests assert on the category phrase.

| Category | Message shape |
|----------|---------------|
| Invalid setting | `Error: invalid <key>: <reason>` (e.g. `invalid rpc_url: scheme must be http or https`) |
| Password without username | `Error: password is set in <config path> but username is not` |
| Config unreadable | `Error: cannot read config file <path>: <reason>` |
| Database unreadable | `Error: cannot read database <path>: <reason>. The file was not changed.` |
| Database write failed | `Error: cannot write to database <path>: <reason>. Transactions recorded before this error were kept.` (e.g. a second run in progress) |
| Newer schema | `Error: database <path> was written by a newer version of monero-income (schema N)` |
| Wallet unreachable | `Error: cannot reach the wallet at <rpc_url>: <reason>` |
| Login rejected | `Error: the wallet at <rpc_url> rejected the login; check username and password` |
| Wallet error | `Error: the wallet returned an error: <wallet message>` |
| Invalid wallet response | `Error: unexpected response from the wallet: <reason>` |
| Interrupted | `Error: interrupted; anything already recorded was kept` |
| Unexpected | `Error: unexpected <ExceptionType>: <message>` |
