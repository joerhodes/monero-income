# Quickstart: validating the transaction export

**Feature**: 003-transaction-csv-export

## Automated

```sh
uv run ruff check && uv run ruff format --check
uv run mypy
uv run lint-imports
uv run pytest            # includes the golden-file tests in tests/golden/
```

All gates must pass (constitution VII). The golden files are the reference for the format in
[contracts/export-csv.md](contracts/export-csv.md).

## By hand, against a real wallet

Prerequisites: feature 001/002 set up (wallet RPC running, config file in place).

| # | Do | Expect |
|---|----|--------|
| 1 | `monero-income` | Last line `Exported N transactions to /Users/you/reports/xmr_income.csv.`; the file exists |
| 2 | `ls -l ~/reports/xmr_income.csv` | `-rw-------` (FR-026) |
| 3 | `head -3 ~/reports/xmr_income.csv` | The header from the contract, then the oldest transactions |
| 4 | `grep -cvE '^[0-9a-f]{64},' ~/reports/xmr_income.csv` | `1` (only the header isn't a data row) |
| 5 | `tail -n +2 ~/reports/xmr_income.csv \| cut -d, -f2- \| grep -c '[eE]'` and `awk -F, 'NF != 7' ~/reports/xmr_income.csv` | `0`, and no output: no exponents outside the txid, and no extra commas from separators (FR-018) |
| 6 | Compare the row count with the database: `sqlite3 ~/.local/share/monero-income/xmr.db 'select count(*) from transactions'` | Equals `N` |
| 7 | `chmod 644 ~/reports/xmr_income.csv && monero-income && ls -l ~/reports/xmr_income.csv` | Back to `-rw-------` |
| 8 | Run twice in a row with no new transactions; `shasum` the file each time | Identical (SC-008), unless a provisional price was refreshed in between |
| 9 | `monero-income --reports-path /tmp/xmr-export-test` | The directory is created; the export is written there |
| 10 | `touch /tmp/not-a-dir && monero-income --reports-path /tmp/not-a-dir` | `Error: cannot write export /tmp/not-a-dir/xmr_income.csv: …`, exit 1; `~/reports/xmr_income.csv` unchanged |
| 11 | Stop the wallet RPC; `monero-income` | Sync error, exit 1; the export's modification time is unchanged (FR-002) |
| 12 | `ls -a ~/reports` after any of the above | No `.xmr_income.csv.*.tmp` files |
| 13 | Read [docs/export-csv.md](../../docs/export-csv.md) with the file open | Every column and value can be explained from the document alone (SC-007) |
