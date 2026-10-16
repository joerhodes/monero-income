# Contract: configuration file

**Location**: `~/.config/monero-income/config.toml` (fixed for this feature).
**Format**: TOML, read with stdlib `tomllib`.

## Keys (feature 001)

```toml
rpc_url  = "http://127.0.0.1:18088/json_rpc"   # string, default shown
username = "monero"                             # string, optional
password = "secret"                             # string, optional; config file only
db_path  = "~/.local/share/monero-income/xmr.db" # string, default shown; ~ expanded
```

| Key | Type | Default | CLI override |
|-----|------|---------|--------------|
| `rpc_url` | string | `http://127.0.0.1:18088/json_rpc` | `--rpc-url` |
| `username` | string | none | `--username` |
| `password` | string | none | none (config file only) |
| `db_path` | string | `~/.local/share/monero-income/xmr.db` | `--db-path` |

## Rules

- **Precedence**: command-line option, then config file, then default.
- **Missing file**: not an error; defaults (and options) apply.
- **Unreadable or invalid TOML**: error, exit 1. The message names the file and the parse
  location, never the file's contents.
- **Wrong type** for a known key: error naming the key and the expected type.
- **Unknown keys**: warning naming the key; the run continues. This lets an older version read
  a config file that has keys added by later features.
- **`password` without `username`** (after precedence): error.
- **`rpc_url`** must be `http` or `https` with a host and must not contain user info
  (`user:pass@`). Credentials belong in `username`/`password`.
- **Permissions**: if the file is readable by others (`mode & 0o004`), print a warning and
  continue.
- **Never echoed**: no message ever includes the `password` value.

## Extension point

Loading is split into (1) reading the TOML file into a raw mapping (primitives, I/O) and
(2) resolving it into a typed `Settings` (orchestration, pure). Later features add keys by
extending the known-key table and `Settings`; the file reading stays the same.
