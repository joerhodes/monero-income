# Research: Transaction CSV Export

**Feature**: 003-transaction-csv-export | **Date**: 2026-10-26

The spec left no `NEEDS CLARIFICATION` markers. These are the design questions planning had
to settle, mostly how to meet FR-007 (all-or-nothing replace), FR-026 (owner-only), and the
exact-formatting requirements with the existing stack.

## R1. Replacing the export atomically

**Decision**: Write the new export to a temporary file in the **same directory**, flush and
`fsync` it, then `os.replace()` it onto `xmr_income.csv`, then `fsync` the directory. On any
exception, including `KeyboardInterrupt`, the temporary file is removed in a `finally` block
and the exception propagates.

**Rationale**: `os.replace` is an atomic rename on POSIX when source and target are on the
same filesystem, which a same-directory temporary file guarantees. Readers see either the old
file or the new one, never a mix (FR-007, the concurrent-runs edge case). `fsync` before the
rename means a crash right after it can't leave an empty or truncated file under the final
name; `fsync` on the directory makes the rename itself durable.

**Alternatives considered**:
- *Write in place (truncate, then write)*: an interruption leaves a partial file. Rejected
  (FR-007).
- *Write to the system temp directory, then move*: may be a different filesystem, where a move
  is a copy and not atomic. Rejected.
- *Back up the old file, then write in place*: two files to reconcile after a crash. Rejected.

## R2. Owner-only permissions (FR-026)

**Decision**: Create the temporary file with `tempfile.mkstemp(dir=..., prefix=".xmr_income.csv.",
suffix=".tmp")`. `mkstemp` creates the file with mode `0o600` regardless of umask, and the
rename keeps that mode, so the export is owner-only every time and is never readable by
others while partial. The previous file's mode is not consulted.

**Rationale**: Satisfies both halves of FR-026 with no extra `chmod` step and no window in
which the file has looser permissions.

**Alternatives considered**: `open()` then `chmod(0o600)`: a brief window with umask
permissions. Rejected.

## R3. Leftover temporary files after a hard kill (FR-007)

A `finally` block covers exceptions and Ctrl-C, but not `SIGKILL` or a power loss, which can
leave a hidden `.xmr_income.csv.*.tmp` file. FR-007 requires that a later successful run not
leave such files behind.

**Decision**: While writing, the run holds an exclusive `fcntl.flock` on the **output directory**
itself (opened `O_RDONLY`). Holding the lock, it first deletes any `.xmr_income.csv.*.tmp`
files, then writes and replaces. The lock is released when the descriptor is closed, including
when the process dies.

**Rationale**: Under the lock no other run can be mid-write, so every matching temporary file
is from a dead run and safe to delete. Locking the directory, not a lock file, leaves nothing
extra in the output directory. A second concurrent run waits for the first (writing takes well
under a second for any realistic wallet), then writes its own complete export; the file left is
complete and from one run (edge case "two runs at the same time"). `flock` on a directory
descriptor works on Linux and macOS, the target platforms.

**Alternatives considered**:
- *Delete temporary files older than N minutes, without a lock*: a run inside the window after
  a crash would still leave the file (violates FR-007), and the threshold is arbitrary.
- *A `.lock` file*: an extra file left in the user's reports directory.
- *A fixed temporary name opened with `O_EXCL`*: a crash leaves the name taken, so every later
  run fails until it's removed by hand.

## R4. Formatting each column exactly

**Decision** (all pure functions over stored values; no `float` anywhere, constitution III):

| Column | Rule |
|--------|------|
| `txid` | Stored text, as is |
| `height` | `str(int)` |
| `timestamp_utc` | `datetime.fromtimestamp(occurred_at, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")` |
| `xmr` | Integer arithmetic on piconero: `f"{p // 10**12}.{p % 10**12:012d}"` |
| `usd_price` | `format(Decimal(stored_text), "f")`, which reproduces the stored plain decimal text (feature 002 stores `format(price, "f")`) |
| `price_status` | Stored `final` / `provisional`, or `TBD` |
| `usd_value` | Feature 002's exact `usd_value(amount, price)`, then `quantize(Decimal("0.01"), ROUND_HALF_UP)` under a local context whose precision covers every digit of the exact value, then `format(…, "f")` |

**Rationale**:
- Format `"f"` never uses an exponent, so `Decimal("1E+2")` is written `100`.
- Neither `str(int)` nor format `"f"` inserts separators (FR-018).
- Integer division keeps `xmr` exact without any Decimal context.
- The default Decimal precision (28 digits) can be too small for `quantize` on an exact product
  of a 12-decimal amount and a long price, which would raise `InvalidOperation`. A local
  context sized to the value avoids that.
- `quantize` to `0.01` always gives exactly two decimals (`188.08`, `0.00`, `185175.00`).

**Alternatives considered**: `str(Decimal)` can produce exponents (`1E+2`). Rejected.

## R5. CSV dialect

**Decision**: stdlib `csv.writer` with `lineterminator="\n"` and default minimal quoting,
UTF-8 with no BOM, and a newline after the last row.

**Rationale**:
- Every value is ASCII with no commas, quotes or line breaks, so nothing is ever quoted.
- LF line endings keep the file readable with `cat`/`less`, diff cleanly in git, and keep the
  golden file stable across platforms. Spreadsheets and CSV readers accept LF.

**Alternatives considered**: CRLF (RFC 4180's line ending) adds `^M` noise in terminal tools
and diffs for no practical gain. Hand-joined strings work today but would silently break if a
future column ever needed quoting.

## R6. Where the export step runs

**Decision**: Last step of `run()`, after pricing. The rows are read on the open connection,
the connection is closed, then the file is written. Any `RunError`, storage or wallet error
earlier in the run raises before this point, so no export is written (FR-002).

**Rationale**:
- Reading after pricing gives the state at the end of pricing (FR-020).
- Closing the database first means a slow or failing file write never holds a database lock
  another run is waiting on.

## R7. Row order

**Decision**: The SQL query returns rows unordered; a pure function sorts by
`(occurred_at, height, txid)` (FR-010, clarified).

**Rationale**: Keeps the order rule in tested pure code (constitution IV). The sort is cheap at
any realistic size (tens of thousands of rows).

## R8. Golden files

**Decision**: A golden file `tests/golden/xmr_income.csv` locks the export's bytes for a
synthetic database. The database covers:

- final, provisional, and unpriced days;
- a half-cent value (rounds up);
- a price stored as `150`;
- a long-precision price;
- a 1-piconero amount;
- a value over 100,000 USD;
- two transactions in the same second;
- a later block with an earlier timestamp.

A second golden file, `tests/golden/xmr_income_empty.csv`, holds the header-only export.

**Rationale**: The constitution requires report output to be locked by golden-file tests.
This is the first report output, so the directory is new. A golden file is a stronger check
than per-column assertions for FR-009/FR-018 and SC-008.

## R9. Reader documentation (FR-023)

**Decision**: A standalone `docs/export-csv.md`, written for an auditor, linked from the
README's Usage section. It covers the file's location, one row per transaction, row order,
each column (meaning, format, units), `TBD`/`provisional`/`final`, the UTC day rule, the
rounding rule with a worked example, and a note on spreadsheets trimming decimals.

**Rationale**: A separate file can be handed to an auditor with the export, without the rest
of the README. It lives under `docs/` beside, not inside, `docs/sdd-log/`.

## R10. Output directory setting

**Decision**:
- **Setting**: a new string config key, `reports_path`, and a new option, `--reports-path`.
  Precedence is option, then file, then the default `~/reports`.
- **Path handling**: `~` is expanded at call time, so the autouse `HOME` fixture keeps tests
  out of the real home directory. The path is made absolute for the run's output line.
- **Validation**: empty, or not a string in the config file, is an error before syncing
  (FR-022), with the same message shapes as `db_path`.
- **Creating the directory**: `mkdir(parents=True, exist_ok=True)` at write time (FR-005).

**Rationale**: Mirrors `db_path` exactly. Whether the directory can be created or written is
only checked at write time: checking earlier could pass and still fail later, and FR-008
already covers the failure.
