# Contract: config key added by feature 003

Added to [feature 001's config file](../../001-sync-incoming-transactions/contracts/config.md)
and [feature 002's keys](../../002-usd-valuation/contracts/config.md). Their rules
(precedence, missing file, permissions warning, unknown-key warning) are unchanged.

```toml
reports_path = "~/reports"   # string, default shown; ~ expanded
```

| Key | Type | Default | CLI override | Validation |
|-----|------|---------|--------------|------------|
| `reports_path` | string | `~/reports` | `--reports-path` | Not a string in the file → `invalid reports_path in <config path>: expected a string`. Empty or blank (after precedence) → `invalid reports_path: must not be empty`. Both exit 1 before syncing (FR-022) |

- **Path handling**: `~` is expanded when settings are resolved. A relative path is relative
  to the current directory. The run's output line shows the absolute path.
- **Checked when writing, not at startup**: whether the directory exists, can be created, or
  is writable. Failures there are export write errors ([cli.md](cli.md)).
- **Shared directory**: later report features are expected to write their files to the same
  directory.
