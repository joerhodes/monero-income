# 08 - Reanalyze After Constitution and Spec Update

**Command:** /speckit-analyze
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-15

## What Came Back
The analysis didn't run because specs/001-sync-incoming-transactions/tasks.md doesn't exist yet. /speckit-analyze checks the spec, plan and tasks against each other, so it needs the task list first. I made no changes.

Before /speckit-tasks, the plan files need updating. They still describe the start date that the spec no longer has:
- the since config key and --since option
- the meta table, whose only key was the start date
- the check_since and discard_before functions
- research R3
- the start-date test scenarios in quickstart.md

If tasks are generated now, they'll include work for the removed start-date feature.

Next steps:
1. Update the plan files to remove the start date. I can do this the same way I removed self transfers, if you'd like.
2. Run /speckit-tasks.
3. Run /speckit-analyze again.


## Prompt to remove start date
The spec changed: the start date was removed. Update the plan artifacts
to match, and remove the meta table, which existed only to hold it;
schema versioning stays on PRAGMA user_version. Also replace the
single-transaction sync with: fetch transfers in ascending block-height
windows and commit each window in its own transaction, so an interrupted
first sync keeps completed windows. Choose a window size in research.md
with rationale. This resolves the OPEN item about large first syncs
timing out. Change nothing unrelated.

## What Came Back
I removed the start date and the meta table from all the plan artifacts, and replaced the single-transaction sync with one commit per height window. A search for start-date and meta references now only finds ordinary uses of the word "since" and the "(removed)" note in research R3.                                                                            

Window size: 10,000 blocks, about 14 days of Monero blocks. The full rationale is in research.md R2, which is now marked resolved:
- Response size: even a miner paid in many blocks a day gets at most a few hundred entries per 
  window, well inside the 20-second timeout.                                                   
- Interruption: an interrupted first sync loses at most one window of progress. 100,000-block windows would mean about 40 requests for a full first sync, but each response would be ten times larger and an interruption could lose about 139 days of progress.
- Request count: a full first sync from height 0 is about 380 requests. Most return nothing, since the wallet's restore height limits its history. A routine daily run is a single request.
- Resuming: the next run starts at the last recorded height minus the 60-block overlap. Already-recorded transaction ids are skipped, so the final records match an uninterrupted sync.

Changes by file:
- research.md: R2 is rewritten as above. R3 is replaced by a short note that the start date was removed; I kept the number so R4–R9 don't change. The window bounds in R5 now use 10,000 blocks, and R7 says schema creation is one transaction and each window's records are another.
- data-model.md:
  - The meta table, Settings.since, discard_before and check_since are removed.
  - Windows are ascending and 10,000 blocks.
  - SyncResult.recorded is summed over all windows.
  - A rare primary-key conflict now rolls back only that window.
  - The run lifecycle is redrawn as a commit-per-window loop.
  - Schema versioning stays on PRAGMA user_version.
- plan.md: the summary, scale estimate, Principle VI row and source-tree comments now describe the per-window commits.
- contracts/:
  - --since, the since config key and the start-date mismatch error are gone.
  - The invalid-setting example now uses rpc_url.
  - Ctrl-C (exit 130) now says completed windows are kept.
- quickstart.md: the two start-date scenarios are removed. The wallet-failure scenario now expects windows 1–2 to stay committed.

Nothing else changed. The next step is /speckit-tasks, then /speckit-analyze.
