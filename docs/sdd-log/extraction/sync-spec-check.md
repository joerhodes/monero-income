# Spec 001 vs Legacy Code — Sync

Spec: `~/Projects/monero-income/specs/001-sync-incoming-transactions/spec.md` (cited as `spec.md:line`).
Code: legacy repo `xmr-income-report` @ `54e77b9` (cited as `path:line`).
(inferred) = depends on monero-wallet-rpc behavior or Python/library behavior not shown in this repo.

Status key: **DIFFERS** = code contradicts spec. **GAP** = code behavior the spec does not address. **MATCH** = noted only where a match is non-obvious.

## Differences

1. **DIFFERS — multi-payment transactions not summed.** Spec: one record per txid with total received across subaddresses (`spec.md:167-170`, `spec.md:131-133`). Code: inserts each wallet entry with `INSERT OR IGNORE`; the first entry for a txid wins, later ones are dropped (`src/monero_tools/db.py:103`, `src/xmr_income_report/report.py:152`). Verified by probe: two entries for one txid → one record with the first amount. Wallet returns one `in` entry per receiving subaddress (inferred).

2. **DIFFERS — no "N recorded" message.** Spec FR-012 requires telling the user how many were recorded (`spec.md:176-177`). Code prints nothing when count > 0 (`src/xmr_income_report/cli.py:139-141`); return value discarded (`src/xmr_income_report/cli.py:85`).

3. **DIFFERS — incomplete "every not-yet-recorded transaction".** Spec FR-002 (`spec.md:154-155`). Code only asks the wallet for transfers above the highest recorded height (`src/xmr_income_report/report.py:138-140`, `src/monero_tools/db.py:121`). Missed cases:
   - another incoming tx at exactly the max recorded height: excluded because the wallet treats `min_height` as exclusive (inferred);
   - txs below max height that appear later (wallet rescan, restored subaddresses, chain reorg to a lower height) (inferred).

4. **DIFFERS — self-transfers may be recorded.** Spec FR-003 excludes transfers from the wallet to itself (`spec.md:156-157`, `spec.md:128`). Code requests `in` only and does not filter self-sends (`src/xmr_income_report/report.py:131-137`). Monero lists a send to one's own subaddress under `in` as well as `out` (inferred).

5. **DIFFERS — first run fails with default storage location.** Spec FR-016 persistence (`spec.md:185`). Default DB parent directory `~/.local/share/xmr-income-report/` is never created (`src/xmr_income_report/report.py:36`, `src/monero_tools/db.py:28`). Verified by probe: `OperationalError: unable to open database file`. Uncaught → traceback (`src/xmr_income_report/cli.py:84`).

6. **DIFFERS — damaged/unreadable local records not reported as a clean error.** Spec edge case (`spec.md:141-142`), FR-015 (`spec.md:182-184`). DB open/table creation is outside any error handler (`src/xmr_income_report/cli.py:84`, `:105-112`) → traceback, not a message (inferred: exit 1 via uncaught exception).

7. **DIFFERS — errors before sync not handled as sync errors.** Spec FR-015 "any error … message … failure status" (`spec.md:182-184`). Malformed config TOML raises uncaught (`src/xmr_income_report/cli.py:59`, `src/xmr_income_report/report.py:65-66`) (inferred: traceback). Invalid `--since` is handled cleanly but exits *before* sync (`src/xmr_income_report/cli.py:76`, `:100-102`).

8. **DIFFERS — login failure not identified as a login problem.** Spec edge case (`spec.md:137-138`). Code shows raw exception text: `Error fetching transfers: <exc>` (`src/xmr_income_report/cli.py:136`); for HTTP 401 this is the generic requests text with the URL (inferred: `401 Client Error: Unauthorized for url: …`).

9. **DIFFERS — password silently ignored without username.** Spec FR-018 optional username/password (`spec.md:188-190`). Auth sent only if username non-empty (`src/xmr_income_report/report.py:142`).

10. **DIFFERS — very large first sync may time out.** Spec edge case: thousands of txs recorded in one run (`spec.md:143-144`). Single RPC call, fixed 20 s timeout, no retry (`src/monero_tools/rpc.py:26`, `src/xmr_income_report/report.py:144-149`). Timeout → sync error, exit 1 (inferred).

## Gaps (code behavior the spec doesn't cover)

11. **GAP — connection settings shape.** Spec leaves the mechanism to planning (`spec.md:223-225`). Code: single full URL (scheme, host, port, path) via `--rpc-url` or config `rpc_url` (`src/xmr_income_report/cli.py:39`, `src/xmr_income_report/report.py:79-80`); HTTP Digest auth (`src/monero_tools/rpc.py:53`); fixed 20 s timeout (`src/monero_tools/rpc.py:26`).

12. **GAP — password exposure via command line.** Spec FR-018 forbids showing the password in output (`spec.md:189-190`); code never prints it. But `--password` is a CLI flag (`src/xmr_income_report/cli.py:41`), visible in process listings and shell history (inferred).

13. **GAP — locked coinbase outputs.** Spec counts any tx in a block (`spec.md:158-160`). Code requests `in`, which includes coinbase/mining payouts that are still locked (inferred); recorded immediately. Spec is silent on spendability; the code behavior matches FR-004 literally.

14. **GAP — extra stored field.** Code also stores a UTC calendar date per tx (`src/monero_tools/db.py:50`, `src/xmr_income_report/report.py:109`). Used later for pricing; not in spec Key Entities (`spec.md:194-199`).

15. **GAP — amount text format.** Spec requires exactness (`spec.md:163-164`). Code is exact but stores the shortest decimal string, including scientific notation for tiny amounts, e.g. `1E-7` (`src/xmr_income_report/report.py:107`, `src/monero_tools/db.py:95`; verified by probe). Not a violation; a rewrite must not copy it into output.

16. **GAP — error message wording.** "No new transfers found." (`src/xmr_income_report/cli.py:140`) and "Error fetching transfers: …" (`src/xmr_income_report/cli.py:136`). Spec gives no wording; legacy uses "transfers", not "transactions".

17. **GAP — wallet JSON-RPC error text.** Displayed as `RPC error {code}: {message}` (`src/monero_tools/rpc.py:18`, `:67`). Spec doesn't define it.

18. **GAP — malformed wallet response.** Missing `result` → `KeyError`, shown as `Error fetching transfers: 'result'` (`src/monero_tools/rpc.py:69`, `src/xmr_income_report/cli.py:136`). Missing `in` → treated as empty (`src/xmr_income_report/report.py:150`). Spec doesn't cover either.

19. **GAP — reorg after recording at a higher height.** Spec covers existing records not being changed (`spec.md:129-130`). It does not cover the checkpoint: if a recorded tx's block is orphaned, the stale higher height stays the checkpoint and can hide txs between the new and old heights (inferred; `src/xmr_income_report/report.py:138-140`).

## Matches worth noting

20. **MATCH — sync always first, no separate command** (`spec.md:150-153`): sync runs before pricing/reporting every run (`src/xmr_income_report/cli.py:85-89`); single command (`src/xmr_income_report/cli.py:37`).

21. **MATCH — unconfirmed excluded** (`spec.md:158-160`, `spec.md:125-127`): `pending`/`pool`/`failed` false (`src/xmr_income_report/report.py:134-136`).

22. **MATCH — interruption atomicity** (`spec.md:178-181`): all new rows of a run are inserted in one transaction and committed once (`src/monero_tools/db.py:103-104`); an interrupted sync records none of that run's new rows, so the next run records them all (inferred: sqlite3 rollback on uncommitted transaction).

23. **MATCH — existing records never modified** (`spec.md:171`): `INSERT OR IGNORE` only (`src/monero_tools/db.py:103`). Delete helpers exist but are never called by the app (`src/monero_tools/db.py:125-134`).

24. **MATCH — "no new" message then continue** (`spec.md:174-175`): yellow message, run continues to pricing (`src/xmr_income_report/cli.py:139-141`, `:86`). Also shown when the wallet is empty (`src/xmr_income_report/report.py:150`), matching `spec.md:135-136`.

25. **MATCH — sync error → message + exit 1, later steps skipped** (`spec.md:182-184`): `src/xmr_income_report/cli.py:135-137`.

26. **MATCH — time-zone-independent moment** (`spec.md:165-166`): wallet Unix seconds stored as INTEGER (`src/monero_tools/db.py:48`, `src/xmr_income_report/report.py:108`).
