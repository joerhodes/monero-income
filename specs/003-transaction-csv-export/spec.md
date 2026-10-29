# Feature Specification: Transaction CSV Export

**Feature Branch**: `003-transaction-csv-export`

**Created**: 2026-10-26

**Status**: Implemented

**Input**: User description: "monero-income records a Monero wallet's incoming transactions
(feature 001) and values them in USD (feature 002). This feature writes a transaction export:
one CSV file listing every recorded transaction with only its essential data. It serves two
purposes: a record for a financial audit, and an additional, human-readable backup layer.
Summaries (monthly CSV and on-screen reports) are a separate, later feature. Restoring from
the export is out of scope. Behaviors: Every run that completes sync and pricing writes the
export, even if some days could not be priced. If the sync fails, or the run fails with an
error, no export is written. Each run replaces the previous export. An interrupted or failed
write never leaves a partial file; the previous export stays intact. The file is
`xmr_income.csv` in the configured output directory. The output directory is read from the
configuration with the key `reports_path` and defaults to `~/reports`. This may can also be
specified as a command option. One row per recorded transaction, oldest first, with a header
row. Columns, in order: txid: the transaction id; height: the block height; timestamp_utc: the
moment of the transaction, ISO 8601 in UTC; xmr: the exact amount, always 12 decimal places;
usd_price: the USD price of 1 XMR for the transaction's UTC day, at full recorded precision;
TBD if the day has no price; price_status: final, provisional, or TBD; usd_value: xmr times
usd_price, rounded to the nearest cent; TBD if the day has no price. Except for usd_value,
every value is exact: together, the columns contain everything needed to rebuild the recorded
transactions and prices without loss. No value is written in scientific notation or with
thousands separators. The export's columns and their meanings are documented for a reader who
has never seen the tool."

## Clarifications

### Session 2026-10-26

- Q: Who should be able to read the export file each time a run replaces it? → A: Owner only
  (read and write for the owner, no access for anyone else), every time it is written.
- Q: If the run records transactions and prices but then can't write the export, should the
  run end with a failure status? → A: Yes. The run shows an error and ends with a failure
  status; recorded transactions and prices are kept, and the previous export stays intact.
  Unlike a price-source problem, a write failure won't resolve itself on a later run.
- Q: When transactions don't arrive in block order by time, what should "oldest first" sort
  the rows by? → A: By `timestamp_utc`, then `height`, then `txid`. Timestamps never step back
  down the file; heights occasionally may.
- Q: When a `usd_value` falls exactly halfway between two cents, which way should it round?
  → A: Half up (0.125 → 0.13, 0.135 → 0.14), the rule an auditor checking by hand or in a
  spreadsheet would apply.
- Q: Should a successful run print a line saying the export was written? → A: Yes: one line
  after the pricing lines with the transaction count and the file's full path, for example
  `Exported 1234 transactions to /Users/you/reports/xmr_income.csv.` (plain count, as in
  features 001 and 002's lines; singular "transaction" for 1).
- Q: What happens when the reports directory is on a filesystem that doesn't support file
  locking (some network shares)? → A: The export fails like any other write failure, with a
  message saying the filesystem doesn't support locking and suggesting writing the export
  locally and copying it. (Decided after `/speckit-analyze` finding U1.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export every recorded transaction after each run (Priority: P1)

A miner runs the tool as usual. After the sync records any new transactions and the pricing
step values them (feature 002), the run writes `xmr_income.csv` to the reports directory. The
file has a header row and one row per recorded transaction, oldest first, giving the
transaction's id, block height, UTC timestamp, exact XMR amount, its day's USD price and
price status, and its USD value rounded to the cent. Days that have no price yet show `TBD`.
The miner can hand this file to an auditor, or keep it as a plain-text copy of their records.

**Why this priority**: This is the feature. Without the file, the recorded transactions and
their valuations exist only inside the tool's local database, which neither an auditor nor a
spreadsheet can read.

**Independent Test**: With three recorded transactions on two UTC days, one day priced
(final) and the other unpriced, run the tool. The reports directory contains `xmr_income.csv`
with a header row and three data rows in time order; the priced rows show the price,
`final`, and the rounded USD value; the unpriced row shows `TBD` in `usd_price`,
`price_status`, and `usd_value`.

**Acceptance Scenarios**:

1. **Given** recorded transactions, **When** a run completes its sync and pricing, **Then**
   `xmr_income.csv` in the reports directory has a header row followed by exactly one row per
   recorded transaction, oldest first.
2. **Given** the export is written, **When** the user reads the header, **Then** it is
   exactly `txid,height,timestamp_utc,xmr,usd_price,price_status,usd_value`.
3. **Given** a transaction of 1.234567890123 XMR at 2026-10-17 14:03:05 UTC, block 3,250,000,
   on a day with a final price of 152.3456 USD, **When** the export is written, **Then** its
   row reads `<txid>,3250000,2026-10-17T14:03:05Z,1.234567890123,152.3456,final,188.08`.
4. **Given** a transaction of exactly 2 XMR, **When** the export is written, **Then** its
   `xmr` value is `2.000000000000`.
5. **Given** a transaction whose day has a provisional price, **When** the export is
   written, **Then** its `usd_price` is that provisional price, its `price_status` is
   `provisional`, and its `usd_value` is computed from that price.
6. **Given** a transaction whose day has no price (temporarily unpriced, or older than the
   price history), **When** the export is written, **Then** its `usd_price`, `price_status`,
   and `usd_value` are each `TBD`.
7. **Given** the price source fails or rate-limits the run (the run still succeeds, per
   feature 002), **When** the run ends, **Then** the export is written, with `TBD` for the
   days still lacking a price.
8. **Given** the sync fails, **When** the run ends, **Then** no export is written and any
   existing export is unchanged.
9. **Given** the run fails with an error after the sync (for example, a storage error during
   pricing, or an invalid price-import file), **When** the run ends, **Then** no export is
   written and any existing export is unchanged.
10. **Given** no transactions are recorded, **When** a run completes its sync and pricing,
    **Then** the export contains only the header row.
11. **Given** the export is written, **When** the run ends, **Then** the run's output says
    the export was written, naming the file and the number of transactions in it.

---

### User Story 2 - Never leave a broken export (Priority: P1)

Each run replaces the previous export with a complete new one. If the run is interrupted
while writing, or the write fails (for example, the disk is full), the previous export
stays exactly as it was; there is never a partially written file in its place. A write
failure is reported as an error and the run ends with a failure status.

**Why this priority**: The export is an audit record and a backup. A truncated file would be
worse than none, because it could be mistaken for a complete record.

**Independent Test**: Write an export, then run the tool so that writing the new export
fails partway. The file at `xmr_income.csv` is byte-for-byte the previous export, no
partially written file is left in the reports directory, and the run ends with an error
message and a failure status.

**Acceptance Scenarios**:

1. **Given** an existing export, **When** a run completes successfully, **Then** the export
   is replaced in full by the new one; nothing from the old file remains.
2. **Given** an existing export, **When** a run is interrupted while writing the new one,
   **Then** `xmr_income.csv` is still the complete previous export.
3. **Given** an existing export, **When** writing the new one fails, **Then**
   `xmr_income.csv` is still the complete previous export, the run shows an error message
   naming the file and the problem, and the run ends with a failure status.
4. **Given** no previous export, **When** writing the first export fails or is interrupted,
   **Then** no `xmr_income.csv` exists afterwards.
5. **Given** an interrupted or failed write, **When** the next run completes successfully,
   **Then** the reports directory holds only the complete new export (no leftover partial
   files from the earlier attempt).
6. **Given** writing the export fails, **When** the run ends, **Then** the transactions and
   prices recorded by that run are kept.
7. **Given** an existing export that the owner made readable by others, **When** a run
   replaces it, **Then** the new export is readable and writable by its owner only.

---

### User Story 3 - Choose where the export is written (Priority: P2)

By default the export goes to `~/reports`. The user can set a different reports directory in
the configuration file with the key `reports_path`, or for a single run with a command-line
option. If the directory doesn't exist yet, the tool creates it.

**Why this priority**: The default works for most users, but a backed-up or synced local
folder is often where the file needs to go. To share the export from a network share that
doesn't support file locking, the user writes it locally and copies it there.

**Independent Test**: Run the tool three times: with no setting (export in `~/reports`), with
`reports_path` set in the config file (export there), and with both the config key and the
command-line option set (export in the option's directory).

**Acceptance Scenarios**:

1. **Given** no `reports_path` in the config file and no option, **When** the export is
   written, **Then** it is written to `~/reports/xmr_income.csv`.
2. **Given** `reports_path` set in the config file, **When** the export is written, **Then**
   it is written to that directory.
3. **Given** both the config key and the command-line option, **When** the export is
   written, **Then** the option's directory is used.
4. **Given** the reports directory doesn't exist, **When** the export is written, **Then** the
   directory (and any missing parent directories) is created and the export is written in it.
5. **Given** the reports directory path names an existing file, or a directory that can't be
   created or written to, **When** the run tries to write the export, **Then** it shows an
   error naming the path and the problem and ends with a failure status, without changing
   any existing export.
6. **Given** a `reports_path` value that isn't a text value, or is empty, **When** the run
   starts, **Then** it shows an error naming the key and ends with a failure status before
   syncing, as with other invalid configuration (feature 001).
7. **Given** a reports directory on a filesystem that doesn't support file locking (some
   network shares), **When** the run tries to write the export, **Then** it shows an error
   saying the filesystem doesn't support file locking and suggesting writing the export
   locally and copying it, and ends with a failure status, without changing any existing
   export.

---

### User Story 4 - A reader who has never seen the tool can understand the export (Priority: P3)

The project's documentation describes the export for an auditor or other reader who has never
used the tool: the file's name and location, what one row represents, and for each column
its meaning, format, and units, including what `TBD`, `provisional`, and `final` mean, which
UTC day a price applies to, and how `usd_value` is rounded.

**Why this priority**: An audit record is only useful if its reader can interpret it. It is
P3 because the file itself is usable without the document by its owner.

**Independent Test**: Give the documentation and a sample export to someone unfamiliar with
the tool. Using only the documentation, they can state, for any row, what each value means
and recompute `usd_value` from `xmr` and `usd_price`.

**Acceptance Scenarios**:

1. **Given** the documentation, **When** a reader looks up any column, **Then** they find its
   meaning, its format, and its units.
2. **Given** the documentation, **When** a reader sees `TBD`, `provisional`, or `final`,
   **Then** they find what each means and whether the value may change in a later export.
3. **Given** the documentation, **When** a reader recomputes a row's `usd_value`, **Then**
   the documented rule (xmr times usd_price, rounded to the cent as documented) gives the
   value in the file.

---

### Edge Cases

- **No transactions recorded**: the export is written with only the header row.
- **Several transactions with the same timestamp**: they are ordered by block height, then by
  transaction id, so the order is the same on every run.
- **Block timestamps out of order with heights** (a later block with an earlier timestamp):
  rows follow `timestamp_utc`, with height breaking ties, so `height` may occasionally step
  back down the file; `timestamp_utc` never does.
- **Price with trailing zeros or very many digits**: `usd_price` is written exactly as
  recorded, at full precision, never in scientific notation (for example, a recorded price of
  150 is written `150`, not `1.5E+2`).
- **Very small amount** (for example, 1 piconero): `xmr` is `0.000000000001`; its
  `usd_value` may round to `0.00`.
- **Large values** (amounts or USD values in the thousands or more): written without
  thousands separators (for example, `1234.56`, never `1,234.56`).
- **`usd_value` exactly halfway between two cents**: rounded half up, so `0.125` becomes
  `0.13` (all values are positive, so half up and half away from zero agree).
- **Provisional price later finalized**: the next export shows the final price and status;
  the export always reflects what is recorded at the end of the run.
- **Day older than the price history with no imported price**: shown as `TBD` in every run's
  export, like a temporarily unpriced day; the documentation explains that `TBD` means no
  price is recorded yet, whatever the reason.
- **Run where pricing made no lookups** (every day already final, or nothing to price): the
  export is still written.
- **Reports directory doesn't exist**: created, including missing parents.
- **Output path is a file, or not writable**: the run fails with an error naming the path;
  any existing export is unchanged.
- **Disk full or other write failure mid-write**: the run fails with an error; the previous
  export stays intact and no partial file is left.
- **Interruption (for example, the user cancels the run) while writing**: the previous export
  stays intact; the next successful run leaves no stray partial file behind.
- **Two runs at the same time**: each writes a complete export; the file left behind is
  complete and comes from one of them, never a mix (feature 001's concurrency rules still
  apply to the database).
- **Reports directory on a filesystem without file locking** (some network shares): the run
  fails with a message saying so (FR-027); any existing export there is unchanged. Write the
  export locally and copy it to the share.
- **Run fails before the export step** (invalid configuration, sync failure, storage error
  during pricing, invalid import file): no export is written; the existing export, if any, is
  unchanged.
- **Previous export had looser permissions** (the owner changed them by hand): the new export
  is owner-only again; to share it, the owner copies it elsewhere.
- **Opening the file in a spreadsheet**: the file's text contains no scientific notation or
  separators; how a spreadsheet chooses to display values (for example, trimming decimals) is
  outside the tool's control and the documentation notes it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every run whose sync and pricing complete MUST write the export, including runs
  where some days could not be priced because of price-source problems (feature 002 FR-009).
- **FR-002**: When the sync fails, or the run fails with an error at any point before the
  export is written (feature 001 FR-015, feature 002 FR-020 and FR-025), the run MUST NOT
  write an export, and any existing export MUST be left unchanged.
- **FR-003**: The export MUST be a single CSV file named `xmr_income.csv` in the reports
  directory.
- **FR-004**: The reports directory MUST be, in order of precedence: the command-line option
  `--reports-path`, then the configuration key `reports_path`, then the default `~/reports`.
  A leading `~` MUST be expanded to the user's home directory, as with `db_path`.
- **FR-005**: If the reports directory doesn't exist, the run MUST create it, including any
  missing parent directories.
- **FR-006**: Each run's export MUST replace the previous export in full.
- **FR-007**: Replacing the export MUST be all-or-nothing: at every moment, including after an
  interruption or a failed write, `xmr_income.csv` MUST either be the complete previous export
  (or absent, if there was none) or the complete new export. A failed or interrupted write
  MUST NOT leave a partial file at `xmr_income.csv`, and a later successful run MUST NOT
  leave behind partial files from an earlier attempt.
- **FR-008**: If the export can't be written (the reports directory can't be created or
  written to, or the write fails), the run MUST show an error naming the path and the problem
  and end with a failure status, even though the sync and pricing succeeded. Transactions and
  prices recorded earlier in the run MUST be kept, and the previous export MUST stay intact
  (FR-007).
- **FR-009**: The file MUST start with exactly one header row,
  `txid,height,timestamp_utc,xmr,usd_price,price_status,usd_value`, followed by exactly one
  row per recorded transaction, and no other rows.
- **FR-010**: Rows MUST be ordered oldest first by `timestamp_utc`, then by `height`, then by
  `txid`.
- **FR-011**: `txid` MUST be the transaction id exactly as recorded.
- **FR-012**: `height` MUST be the recorded block height as a whole number.
- **FR-013**: `timestamp_utc` MUST be the recorded moment of the transaction in ISO 8601,
  in UTC, to the second, in the form `YYYY-MM-DDTHH:MM:SSZ`.
- **FR-014**: `xmr` MUST be the exact recorded amount in XMR with exactly 12 decimal places
  (for example, `2.000000000000`).
- **FR-015**: `usd_price` MUST be the recorded USD price of 1 XMR for the transaction's UTC
  calendar day, written exactly at its full recorded precision, or `TBD` if that day has no
  recorded price.
- **FR-016**: `price_status` MUST be `final` or `provisional`, matching the day's recorded
  price, or `TBD` if the day has no recorded price.
- **FR-017**: `usd_value` MUST be the exact product of the transaction's XMR amount and its
  day's USD price, rounded to the nearest cent, half up, and written with exactly 2 decimal
  places; or `TBD` if the day has no recorded price.
- **FR-018**: Values MUST NOT be written in scientific notation or with thousands
  separators.
- **FR-019**: Except for `usd_value`, every value MUST be exact, so that the recorded
  transactions (id, height, moment, amount) and the recorded daily prices (date, price,
  status) for every day with a transaction can be rebuilt from the export without loss.
- **FR-020**: The export MUST reflect the recorded transactions and prices as they stand at the
  end of the run's pricing (and import, if any).
- **FR-021**: After writing the export, the run MUST print one line, after feature 002's
  pricing lines, saying the export was written, with the number of transactions it contains
  and the file's full path (for example,
  `Exported 1234 transactions to /Users/you/reports/xmr_income.csv.`). The count MUST be
  written without thousands separators, and "transaction" MUST be singular when the count
  is 1. A run that writes no export MUST NOT print this line.
- **FR-022**: An invalid `reports_path` configuration value (not a text value, or empty) MUST
  be reported as an error naming the key, and the run MUST end with a failure status before
  syncing, as for other invalid configuration (feature 001).
- **FR-023**: The project's documentation MUST describe the export for a reader who has never
  seen the tool: the file's name and location, what a row represents, the row order, and for
  each column its meaning, format, and units, including the meaning of `TBD`, `provisional`,
  and `final`, which UTC day a price applies to, and the `usd_value` rounding rule.
- **FR-024**: Writing the export MUST NOT change any recorded transaction or price.
- **FR-025**: User-facing messages MUST refer to "transactions", never "transfers" (as in
  features 001 and 002).
- **FR-026**: Every time the export is written, it MUST be readable and writable by its owner
  only, with no access for other users, whatever permissions the previous export had. A
  partially written file MUST NOT be readable by other users at any point either.
- **FR-027**: If the reports directory's filesystem doesn't support file locking, the export
  MUST fail as in FR-008, with an error that names the path, says the filesystem doesn't
  support file locking (for example, some network shares), and suggests writing the export
  to a local directory and copying it. The reader documentation (FR-023) MUST describe this
  limitation.

### Key Entities

- **Transaction export**: The file `xmr_income.csv` in the reports directory. A complete
  snapshot, written at the end of each successful run, of every recorded transaction with its
  valuation. Replaced in full by each run; never partially written.
- **Export row**: One recorded transaction (feature 001) joined with its UTC day's price
  (feature 002), if any. Fields: transaction id, block height, UTC timestamp, exact XMR
  amount, USD price, price status, and USD value rounded to the cent.
- **Reports directory**: Where the export is written. Set by command-line option, then the
  `reports_path` configuration key, then the default `~/reports`. Later report features are
  expected to write to the same directory.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After every run whose sync and pricing complete, the export contains 100% of
  recorded transactions, each exactly once.
- **SC-002**: For 100% of rows, the transaction id, height, moment, and amount rebuilt from
  the export match the recorded transaction exactly, and for 100% of days with a
  transaction, the price and status rebuilt from the export match the recorded price exactly.
- **SC-003**: For 100% of priced rows, `usd_value` differs from the exact product of `xmr`
  and `usd_price` by at most half a cent.
- **SC-004**: 0 values in the export use scientific notation or thousands separators.
- **SC-005**: Across interruptions or write failures at any point during writing, 0 runs
  leave a partial `xmr_income.csv`; the file is always either the complete previous export
  or the complete new one.
- **SC-006**: 0 exports are written by runs that fail (sync failure or any error).
- **SC-007**: A reader who has never seen the tool can, using only the documentation, state
  the meaning of every column and recompute any row's `usd_value`.
- **SC-008**: Running the tool twice with no new transactions and no price changes produces
  byte-identical exports.
- **SC-009**: After 100% of runs that write the export, other users have no access to it.

## Assumptions

- **Exact timestamps**: feature 001 records each transaction's moment to the whole second, so
  `YYYY-MM-DDTHH:MM:SSZ` is exact.
- **Price precision**: `usd_price` is written as recorded, without padding or trimming to a
  fixed number of decimals, so it is exact.
- **What "rebuild without loss" covers**: the transactions and the prices of days that have
  transactions (date, price, status). Where a price came from (the price source or an import)
  is not part of the essential data and is not exported. Restoring from the export is out of
  scope.
- **One status for unpriced days**: `TBD` covers both temporarily unpriced days and days
  older than the price history; the run's own messages (feature 002) already distinguish them.
- **File format**: comma-separated, UTF-8 text, with no quoting needed (no value contains a
  comma, quote, or line break). Line endings and other byte-level details are set in
  [contracts/export-csv.md](contracts/export-csv.md) (LF line endings, no byte-order mark)
  and locked by golden-file tests.
- **Golden files**: the export is report output under the constitution, so its format is
  locked by golden-file tests created in this feature.
- **Documentation location**: the column documentation lives with the project's user
  documentation (for example, the README or a dedicated document); planning decides where.
  The CSV file itself contains no comments or notes, so it stays a plain table.
- **Run output**: feature 001 and 002's lines are unchanged; the export line (FR-021) is the
  only addition to a successful run's output.
- **Missing reports directory**: created automatically, since the default `~/reports` won't
  exist on a first run.
- **Out of scope**: monthly or weekly summaries, on-screen reports, other file formats,
  filtering or date ranges, choosing a different file name, and restoring from the export.
