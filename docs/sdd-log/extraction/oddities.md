# Oddities — legacy `xmr-income-report`

Legacy repo @ `54e77b9`. Citations are `path:line` in that repo. (inferred) = not read directly from code. "verified" = reproduced by running legacy functions on sample data.
Ordered roughly by impact.

## Likely bugs

1. **First run crashes with default DB path.** Parent dir of `~/.local/share/xmr-income-report/xmr.db` is never created; `sqlite3.connect` fails with "unable to open database file" and a traceback (`src/xmr_income_report/report.py:36`, `src/monero_tools/db.py:28`, `src/xmr_income_report/cli.py:84`). Verified.

2. **Multi-entry transactions lose amounts.** Several wallet entries with the same txid: only the first is stored (`src/monero_tools/db.py:103`). Verified. Wallet emits one entry per receiving subaddress (inferred).

3. **Height checkpoint can skip transactions.** Only transfers above `MAX(height)` are requested (`src/xmr_income_report/report.py:138-140`). Never fetched again:
   - same-height txs, since wallet `min_height` is exclusive (inferred);
   - txs that appear below the checkpoint later (rescan, reorg) (inferred).

4. **DST fall-back misorders rows.** Sort key is local naive `(date, time)` (`src/xmr_income_report/report.py:253`); during the repeated hour a later tx can sort before an earlier one (inferred).

5. **`--since` mixes UTC and local.** Filter uses UTC date (`src/xmr_income_report/report.py:232`); everything else uses local dates. A row dated before `--since` can appear. Verified.

6. **Invalid timezone found late.** Timezone is first used after sync and pricing (`src/xmr_income_report/report.py:227`), so the run does network work then dies with a traceback. Verified.

7. **Self-sends recorded as income.** Only `in` requested, no self-transfer filter (`src/xmr_income_report/report.py:131-137`). Self-sends to own subaddress appear in `in` (inferred).

## Inconsistencies

8. **Unpriced representation differs by column.** `usd_price` empty but `usd_value` `TBD` in the same row (`src/xmr_income_report/report.py:263`, `:272`). Verified.

9. **XMR number format is variable.** `str(Decimal)` gives `2`, `0.5`, `1E-7` (`src/xmr_income_report/report.py:107`, `src/monero_tools/db.py:95`, `src/xmr_income_report/cli.py:206`). Scientific notation reaches the DB, CSV, and screen. Verified.

10. **Failure count wording.** "Failed to fetch prices for N transaction dates" counts days, not transactions (`src/xmr_income_report/cli.py:192`).

11. **"Fetched N new prices." always green.** Shown even when some lookups failed (`src/xmr_income_report/cli.py:158`). The failure warning appears only after all tables (`src/xmr_income_report/cli.py:190-193`).

12. **No count shown for new transfers.** `_new_transfers` returns the count, but `run` discards it (`src/xmr_income_report/cli.py:85`, `:139-141`).

13. **"Transfers" vs "transactions".** Messages say "transfers" (`src/xmr_income_report/cli.py:136`, `:140`); the price warning says "transaction dates" (`src/xmr_income_report/cli.py:192`).

14. **Default timezone hard-coded.** America/Chicago instead of the machine's zone (`src/xmr_income_report/report.py:83`).

15. **Empty values can't override.** Merge uses `or`, so an empty CLI value falls back to config (`src/xmr_income_report/report.py:79-91`). Example: `--username ""` cannot disable auth configured in the file.

16. **Password without username ignored silently** (`src/xmr_income_report/report.py:142`).

17. **`min_request_delay` looks for a CLI override that doesn't exist.** `overrides.get("min_request_delay")` (`src/xmr_income_report/report.py:91`) but there is no such flag (`src/xmr_income_report/cli.py:39-56`).

18. **`--since` accepts more than documented.** Help says `YYYY-MM-DD` (`src/xmr_income_report/cli.py:50`) but `fromisoformat` accepts `20240115`, `2024-W03-1` (`src/xmr_income_report/cli.py:99`). Verified.

19. **`--since` scope is partial.** Filters reports only; sync and pricing still process all history (`src/xmr_income_report/cli.py:85-87`). CSVs are overwritten with the subset (`src/xmr_income_report/report.py:268`).

## Rate limiting / pricing

20. **Backoff docstring wrong.** Says "2, 4, 8 …" (`src/monero_tools/coingecko.py:46`); actual is 1, 2, 4, 8, 16 (`src/monero_tools/coingecko.py:78`).

21. **Sleeps after final 429.** After the last attempt it still sleeps before raising (`src/monero_tools/coingecko.py:77-81`, `:95`). Worst case ~31 s wasted per day.

22. **No circuit breaker.** When rate-limited, every remaining day still gets 5 attempts (`src/xmr_income_report/report.py:188-201`). Runs can take minutes.

23. **Global rate-limit state.** Module-level `_last_request_time` (`src/monero_tools/coingecko.py:19`, `:58`); shared across callers, needs resets in tests (`tests/monero_tools/test_coingecko.py:233`).

24. **Price precision passes through float.** JSON number → float → `str` → Decimal (`src/monero_tools/coingecko.py:84`, `:87`). "Full precision" is float precision (inferred: `response.json()` yields floats).

25. **Pro-only key header.** Always `x-cg-pro-api-key` (`src/monero_tools/coingecko.py:64`). Demo-tier keys use a different header (inferred, external API).

26. **USD value precision cap.** Product uses default 28-digit Decimal context (`src/xmr_income_report/report.py:237`). Verified: a 31-digit exact product is rounded. Negligible in practice.

## Error handling

27. **Unhandled failure paths produce tracebacks** (inferred: no handler around these calls):
    - malformed TOML (`src/xmr_income_report/cli.py:59`);
    - DB open/schema (`src/xmr_income_report/cli.py:84`);
    - timezone (`src/xmr_income_report/report.py:227`);
    - CSV write (`src/xmr_income_report/cli.py:88`).

28. **Broad `except Exception`** in sync and pricing wrappers (`src/xmr_income_report/cli.py:135`, `:159`). Programming errors look like wallet/price failures.

29. **Unescaped markup.** User input and exception text go into `rich` markup strings (`src/xmr_income_report/cli.py:101`, `:136`, `:160`). Bracketed text could be styled or dropped (inferred).

30. **Password on command line.** `--password` flag (`src/xmr_income_report/cli.py:41`) exposes it in process lists and shell history (inferred).

31. **Fixed 20 s wallet timeout, single call** (`src/monero_tools/rpc.py:26`, `src/xmr_income_report/report.py:144-149`). Large first syncs could time out (inferred).

32. **CSV writes are not atomic.** In-place writes, no explicit encoding (`src/xmr_income_report/report.py:268`, `:285`). Crash mid-write leaves partial files (inferred).

## Stale / dead artifacts

33. **README is stale.**
    - Documents `--cache-file` / "price cache JSON", which no longer exist (`README.md:63`).
    - Omits `--db-path`.
    - Says weekly and monthly only; yearly is also printed (`README.md:13`, `src/xmr_income_report/cli.py:188`).

34. **Version and description stale.** `pyproject.toml` version `0.1.0` on branch `v.0.3` (`pyproject.toml:3`). Description and CLI help mention week/month only (`pyproject.toml:4`, `src/xmr_income_report/cli.py:32`).

35. **`summarise` docstring wrong.** Says it returns `(weekly_totals, monthly_totals)`; it returns three dicts (`src/xmr_income_report/report.py:307-309`).

36. **`main.py` is a hello-world stub** (`main.py:1-6`).

37. **Unused DB helpers.** `clear_transfers_table`, `update_price`, `clear_prices_table` are not used by the app (`src/monero_tools/db.py:125`, `:163`, `:196`).

38. **`db_path` missing from template.** Supported in config (`src/xmr_income_report/report.py:85`) but not in `config.toml.example`.

39. **CLI excluded from coverage** (`pyproject.toml:31`), although `tests/xmr_income_report/test_cli.py` exists.

40. **Unseeded Faker in DB tests** (`tests/monero_tools/test_db.py:16`). Non-deterministic data.

41. **Misleading test docstring.** Mentions a "non-zero exit code" from `fill_missing_prices`, which returns a tuple (`tests/xmr_income_report/test_cli.py:131`).
