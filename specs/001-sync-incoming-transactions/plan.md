# Implementation Plan: Sync Incoming Wallet Transactions

**Branch**: `001-sync-incoming-transactions` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-sync-incoming-transactions/spec.md`

## Summary

Every run of `monero-income` begins with a sync. The sync reads incoming transactions from a
user-run `monero-wallet-rpc` (JSON-RPC over HTTP, optional Digest auth) and records each new
one in a local SQLite database. Each record holds the txid, height, exact piconero amount, and
UTC timestamp. The wallet is read in 100,000-block height windows, starting 60 blocks below
the last recorded height (from height 0 on a first run). Entries are filtered and combined by
pure functions: entries before the start date dropped, amounts summed
per txid, already-recorded txids dropped. The new rows are inserted in a single transaction.
Settings come from CLI options, then `~/.config/monero-income/config.toml`, then defaults.
Every failure ends as a one-line message with a non-zero exit, never a traceback.

## Technical Context

**Language/Version**: Python 3.13+, managed with uv

**Primary Dependencies**: Typer (CLI), httpx (HTTP client with Digest auth, research R1);
stdlib `sqlite3`, `tomllib`, `json`

**Storage**: SQLite file, default `~/.local/share/monero-income/xmr.db` (`db_path`); schema
version in `PRAGMA user_version`

**Testing**: pytest, pytest-socket (`--disable-socket`), pytest-cov (coverage floor),
`typer.testing.CliRunner` for the thin CLI only; fakes behind `typing.Protocol`; in-memory
SQLite

**Static gates**: ruff (lint + format), mypy `--strict`, import-linter

**Target Platform**: Linux and macOS desktop/server, run by the wallet owner

**Project Type**: CLI application (single package, `src/` layout)

**Performance Goals**: A sync with nothing new, against 10,000 recorded rows, finishes in under
5 s excluding wallet time (SC-006). Achieved by an indexed max-height lookup and a txid lookup
limited to candidate rows.

**Constraints**: No float for amounts. Never print the password. Never show a traceback. No
network access in tests. 20 s timeout per wallet request. Never modify or delete rows.

**Scale/Scope**: One wallet. Up to about 10⁴ recorded transactions; a full first scan of
roughly 35–40 window requests.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below).*

Checked against constitution v1.2.0.

| Principle | Status | How the design complies |
|-----------|--------|-------------------------|
| I. Layered architecture | ✅ | `primitives/` (wallet RPC, config file reading, database), `orchestration/` (settings, sync, run), `cli.py`. import-linter `layers` contract plus a `forbidden` contract cli → primitives, to enforce "no skipping" (research R8). |
| II. Thin CLI | ✅ | `cli.py` maps options to `CliOptions`, calls `run()`, prints the result or error. `run()` is fully testable without Typer ([contracts/run-api.md](contracts/run-api.md)). |
| III. Exact money | ✅ | No float anywhere. Amounts are exact `int` piconero (integer atomic units, permitted since v1.2.0) in memory and in SQLite. Conversion to XMR (`Decimal`) happens only at output, which this feature doesn't have. |
| IV. Separate I/O from transformation | ✅ | Wallet fetch returns raw JSON; parsing, filtering, combining, windowing, and settings resolution are pure functions ([data-model.md](data-model.md)). The UTC date column is computed by SQLite, not in an I/O function. |
| V. Testable without the network | ✅ | `WalletRpc` Protocol plus `FakeWalletRpc`; HTTP adapter tested with `httpx.MockTransport`; pytest-socket enforced. Database tests use in-memory SQLite, plus `tmp_path` files for the FR-016 file-handling rules (permitted since v1.2.0); no test reads the real config or database paths. |
| VI. Data safety | ✅ | Insert-only, txid primary key, one transaction per sync, migrations keyed on `user_version`, unreadable files never recreated, newer schemas refused. |
| VII. Automated gates | ✅ | All five gates are configured in `pyproject.toml`, with a 90% coverage floor. |
| Constraints | ✅ | Python 3.13+/uv. Only the user's own wallet RPC at a configured URL (default `127.0.0.1`). No price API in this feature. Synthetic fixtures only. |
| Workflow / golden files | ✅ | No report output in this feature, so no golden files are created or changed. |

**Resolved notes**: The Principle III (integer atomic units) and Principle V (temporary files
in tests) conflicts were resolved by the v1.2.0 amendment. The coverage floor is set at 90%.

**Post-design re-check**: unchanged. Phase 1 introduced no new deviations.

## Project Structure

### Documentation (this feature)

```text
specs/001-sync-incoming-transactions/
├── plan.md              # This file
├── research.md          # Phase 0: OPEN items resolved + wallet RPC findings
├── data-model.md        # Phase 1: schema, in-memory types, pure transforms, lifecycle
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── cli.md           # command, options, output lines, exit codes, error categories
│   ├── config.md        # TOML keys, precedence, validation, permissions warning
│   ├── wallet-rpc.md    # JSON-RPC calls used, WalletRpc Protocol, error mapping
│   └── run-api.md       # run(), CliOptions, Reporter, SyncResult, RunError
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks; not created here)
```

### Source Code (repository root)

```text
pyproject.toml                      # deps, [project.scripts] monero-income, ruff/mypy/pytest/
                                    #   coverage/import-linter config (source of truth)
src/monero_income/
├── __init__.py
├── cli.py                          # Typer app; options → CliOptions → run(); prints; exit codes
├── orchestration/
│   ├── __init__.py                 # public API: run, CliOptions, Reporter, SyncResult, RunError
│   ├── run.py                      # run(): settings → database → sync; translates primitive errors
│   ├── settings.py                 # pure: precedence, validation, permission check → Settings
│   ├── sync.py                     # sync(): reads position, fetches windows, inserts new rows
│   ├── transform.py                # pure: windows, since filter, combine, select new
│   └── errors.py                   # RunError
└── primitives/
    ├── __init__.py
    ├── config_file.py              # read TOML → raw mapping + file mode (I/O only)
    ├── wallet_rpc.py               # WalletRpc Protocol, HttpWalletRpc (httpx), wallet errors
    ├── wallet_entries.py           # pure: raw JSON entries → IncomingEntry
    ├── database.py                 # open_database, read position/txids/meta, insert batch
    ├── migrations.py               # schema steps keyed by user_version (0 → 1)
    └── models.py                   # IncomingEntry, TransactionRecord

tests/
├── fakes/wallet.py                 # FakeWalletRpc (exact min/max height semantics, fault injection)
├── unit/                           # transform, settings, wallet_entries, migrations (in-memory)
├── adapters/                       # HttpWalletRpc via httpx.MockTransport; database file rules (tmp_path)
├── integration/                    # run() end to end with fakes + in-memory SQLite (spec scenarios)
└── cli/                            # CliRunner: output lines, exit codes, no traceback, no password
```

**Structure Decision**: A single package in `src/` layout, with the three layers fixed by
constitution I and the planning input. Primitives also hold pure parsing (`wallet_entries.py`)
next to the I/O modules they serve. That keeps fetch functions free of reshaping (IV) without
creating a fourth layer.

## Complexity Tracking

No violations. The earlier constitution conflicts were resolved by amendment (v1.2.0), not
justified here.
