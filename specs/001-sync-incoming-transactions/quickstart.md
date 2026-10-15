# Quickstart: validating feature 001 (sync)

A run and validation guide, not an implementation guide. Behavior details are in
[contracts/](contracts/) and [data-model.md](data-model.md).

## Prerequisites

- Python 3.13+ and `uv`.
- For the manual checks only: a running `monero-wallet-rpc` with a wallet open, preferably a
  **stagenet or testnet** wallet, never a wallet whose data you'd mind appearing in a
  terminal.

## 1. Automated gates (no network)

```sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run lint-imports
uv run pytest            # --disable-socket and the coverage floor come from pyproject.toml
```

All five must pass (constitution VII). `pytest-socket` fails any test that opens a socket.

## 2. Scenario tests (automated, via `run()` with fakes)

Each acceptance scenario in `spec.md` maps to a test that calls `run()` with `FakeWalletRpc` and
an in-memory database:

| Scenario | Expected |
|----------|----------|
| US1-1 First run, wallet has incoming entries | All recorded; `Recorded N new transactions.` |
| US1-2 Incoming + outgoing | Only incoming recorded |
| US1-4 Amount `123456789012` piconero | Stored exactly `123456789012` |
| US2-1 Second run, no changes | Rows identical; `No new transactions found.`; exit 0 |
| US2-2 New entry above last height | Only it added |
| Overlap: entry re-mined 30 blocks lower | Not duplicated, existing row unchanged |
| Multi-subaddress txid | One row, summed amount |
| US3-1 Wallet fails on the 3rd window | `RunError`; windows 1–2 stay committed; the next run equals an uninterrupted run |
| US3-2 Wallet unreachable / login rejected | Matching error category; exit 1 |
| Password without username | Error before any wallet call |

## 3. Manual end-to-end check against a real wallet (stagenet)

```sh
# wallet side (example)
monero-wallet-rpc --stagenet --wallet-file ~/stagenet/w --rpc-bind-port 18088 \
  --rpc-login monero:secret

# config
mkdir -p ~/.config/monero-income
printf 'username = "monero"\npassword = "secret"\n' > ~/.config/monero-income/config.toml
chmod 600 ~/.config/monero-income/config.toml
```

| Step | Command | Expected |
|------|---------|----------|
| First run | `uv run monero-income --db-path /tmp/mi.db` | `Recorded N new transactions.` and exit 0; `/tmp/mi.db` created |
| Repeat | same | `No new transactions found.` and exit 0 |
| Compare | `sqlite3 /tmp/mi.db 'select count(*), sum(amount_piconero) from transactions'` | Matches the wallet's incoming total (`get_transfers` with `in` only) |
| Wrong password | edit the config, rerun | `Error: … rejected the login …`, exit 1, no traceback, no password in output |
| Wallet stopped | stop the wallet, rerun | `Error: cannot reach the wallet at …`, exit 1 |
| Ctrl-C mid-run | interrupt a first run on a fresh `--db-path` | Exit 130; rerun completes and matches the uninterrupted result |
| Loose permissions | `chmod 644` the config, rerun | `Warning: … readable by other users …`, run continues |
| Damaged DB | `echo junk > /tmp/bad.db; uv run monero-income --db-path /tmp/bad.db` | `Error: cannot read database …`; the file still contains `junk` |

Delete `/tmp/mi.db` afterwards. Real wallet data and database snapshots must never be
committed (constitution: Constraints).
