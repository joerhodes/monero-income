# Research: Sync Incoming Wallet Transactions

**Feature**: 001-sync-incoming-transactions | **Date**: 2026-10-14

This file resolves only the items marked OPEN in the planning input, plus findings about the
wallet RPC that affect decided behavior. Wallet behavior was checked against the Monero source
(`monero-project/monero`, `master`): `src/wallet/wallet_rpc_server.cpp`,
`src/wallet/wallet_rpc_server_commands_defs.h`, and `src/wallet/wallet2.cpp`.

## R1. HTTP client (OPEN)

- **Decision**: `httpx`, used synchronously, with `httpx.DigestAuth` when a username is
  configured and `httpx.Timeout(20.0)` per request.
- **Rationale**: Built-in HTTP Digest auth (MD5, `qop=auth`, which is what monero-wallet-rpc
  uses). Ships type hints, so it works under `mypy --strict` without stub packages.
  `httpx.MockTransport` lets the adapter's own tests feed canned responses without opening a
  socket, so they pass under `pytest-socket`. Distinct exception types (`ConnectError`,
  `TimeoutException`) map cleanly to "wallet unreachable", and a final `401` after the digest
  handshake maps to "login failed".
- **Alternatives considered**:
  - `requests` + `HTTPDigestAuth`: works, but needs `types-requests` for mypy and has no
    in-process transport for socket-free adapter tests.
  - stdlib `urllib.request` + `HTTPDigestAuthHandler`: no dependency, but awkward error
    surface (HTTPError vs URLError vs socket errors), no typed response model, and testing
    needs monkeypatching.

## R2. Avoiding timeouts on a large first sync (resolved)

- **Decision**: Fetch in ascending block-height windows and commit each window in its own
  database transaction. Call `get_height` once, then for each window `(lo, hi]` in ascending
  order: call `get_transfers` with `filter_by_height=true`, combine and filter the entries,
  insert the new records, and commit before requesting the next window. Every request keeps
  the default 20-second timeout. **Window size: 10,000 blocks** (about 14 days at Monero's
  2-minute block time).
- **Rationale for the window size**:
  - *Response size*: even a P2Pool miner paid in many blocks a day gets at most a few hundred
    entries per 14-day window, a small response far inside the 20-second timeout.
  - *Work kept on interruption*: committed windows survive, so an interrupted first sync
    loses at most one window's progress. A smaller window keeps more.
  - *Request count*: a first sync from height 0 at the current chain height (about 3.8
    million) is about 380 requests. Each is a local, in-memory lookup in the wallet, and most
    are empty, since the wallet's restore height limits its history. A routine daily run
    (about 720 new blocks plus the 60-block overlap) is a single request.
  - 100,000 blocks (about 139 days) would cut a first sync to about 40 requests, but each
    response would be ten times larger and an interruption would lose up to 139 days of
    progress. 1,000 blocks would mean about 3,800 requests for little extra safety.
- **Interruption behavior**: windows are ascending and each commits before the next, so every
  completed window is kept. The next run resumes from the last recorded height minus the
  60-block overlap (R5) and re-reads at most the unfinished window plus the overlap.
  Already-recorded txids are skipped, so the final records match an uninterrupted sync
  (FR-013, FR-014, SC-004).
- **Alternatives considered**:
  - A longer timeout on the first run: no bound exists that is guaranteed to be enough, and it
    doesn't help a later run after months offline.
  - Fetching all windows, then inserting everything in one transaction (the earlier design):
    an interrupted first sync keeps nothing.
  - Windows sized by expected transaction count: needs a count the wallet RPC doesn't expose
    cheaply; fixed block windows are simpler and predictable.
- **Consequence**: the sync position comes only from the last recorded height. A wallet with
  no recorded transactions yet rescans from height 0 on each run; this is correct, just not
  minimal.

## R3. Start date (removed)

The spec no longer has a start date (Clarifications, 2026-10-15). The wallet's restore height
limits its history, so there is nothing to map to a height and no timestamp filter.

## R4. Self transfers (no longer researched)

The spec no longer excludes self transfers (FR-003; see its Assumptions). The tool reads a
view-only wallet, and change from a rare spend is recorded like any other incoming
transaction. The design uses the decided request (`in=true, out=false, pending=false,
failed=false, pool=false`) and has no self-transfer detection.

## R5. `get_transfers` height filter bounds (finding)

- `wallet2::get_payments` keeps an entry when `min_height < height <= max_height`:
  **`min_height` is exclusive**, `max_height` is inclusive.
- **Consequence for the decided overlap**: "from the last recorded height inclusive, minus 60
  blocks" means the first window's `min_height = max(last_height - 61, 0)`. Windows are
  `(lo, lo + 10000]`, so consecutive windows neither overlap nor leave gaps.
- With `filter_by_height=false`, the server uses `min_height=0`, so a transaction at height 0
  is never returned either way. Only the genesis block is at height 0, so nothing is lost.

## R6. Other wallet response facts used by the design (findings)

- Each `in` entry is one `(txid, subaddress)` pair: a transaction paying several subaddresses
  yields several entries with the same `txid`, `height`, and `timestamp`. Summing by txid (as
  decided) gives the wallet's total; all entries for one txid fall in the same height window.
- `amount` is a `uint64` in atomic units (piconero). Python's `json` parses it as an exact
  `int`. SQLite `INTEGER` is signed 64-bit, so a per-transaction total above
  9,223,372,036,854,775,807 piconero (about 9.2 million XMR) can't be stored. That is far
  above any real payout; the design rejects it with a storage error instead of overflowing.
- `timestamp` is the block's timestamp in Unix seconds (UTC by definition), as recorded by
  the wallet when it scanned the block.
- `type` is `"block"` for coinbase (solo mining) outputs and `"in"` otherwise. Both are
  incoming and both are recorded.
- `get_transfers` defaults to `account_index=0` with `all_accounts=false`, so the decided
  request returns only account 0's incoming entries. A wallet that receives payouts in other
  accounts would need `all_accounts=true`; that isn't part of the decided request. This is
  intended; see the spec's Assumptions (account 0 only).
- `pending=false, failed=false, pool=false` exclude unconfirmed entries; `in` comes only from
  confirmed blocks, which matches FR-004 (one confirmation).
- On a chain reorganization the wallet drops entries above the fork point and re-adds them
  when re-mined. The 60-block overlap re-reads that range; already-recorded txids are skipped,
  and existing rows are never changed (FR-009).
- Errors arrive as a JSON-RPC `error` object (`code`, `message`), for example "No wallet file"
  when no wallet is open. An HTTP `401` after the digest handshake means the login was
  rejected or is required but missing.

## R7. SQLite usage details (supporting the decided storage design)

- Open with `sqlite3.connect(..., autocommit=False)` (Python 3.12+), so every write runs in an
  explicit transaction that `commit()` closes. Schema creation and `PRAGMA user_version` are
  written in one transaction. Each height window's new records are written in their own
  transaction (R2).
- Missing vs unreadable: if the file doesn't exist, create the parent directory and open with
  URI `mode=rwc`. If it exists, open with `mode=rw` and read `PRAGMA user_version`; a
  `sqlite3.DatabaseError` ("file is not a database") becomes a storage error. An existing file
  is never recreated or replaced.
- A `user_version` higher than the newest known schema means a newer tool wrote the file;
  report an error rather than guess.
- The UTC calendar date is a `STORED` generated column, `date(occurred_at, 'unixepoch')`, so it
  can never disagree with the timestamp. It needs SQLite 3.31+; every Python 3.13 build ships
  a newer SQLite.

## R8. Enforcing "no skipping" with import-linter

- A `layers` contract (`cli` above `orchestration` above `primitives`) forbids upward imports
  but allows a higher layer to import any lower layer. "No skipping" therefore also needs a
  `forbidden` contract: `monero_income.cli` must not import `monero_income.primitives`.

## R9. Never showing a traceback

- The CLI wraps its call to `run()`: `RunError` is shown as `Error: <message>` with exit 1,
  `KeyboardInterrupt` as an interruption message with exit 130, and any other exception (a
  bug) as `Error: unexpected <ExceptionType>: <message>` with exit 1. Typer's pretty exception
  output is turned off (`pretty_exceptions_enable=False`). Click's own usage errors (for
  example, an unknown option) already print a usage message without a traceback, with exit 2.
- To keep the password out of all output, `rpc_url` may not contain user info
  (`user:pass@host`). Such a URL is rejected as invalid settings, so no exception text that
  quotes the URL can carry a password.
