# Feature Specification: Sync Incoming Wallet Transactions

**Feature Branch**: `001-sync-incoming-transactions`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "monero-income is a command-line tool that records a Monero
wallet's incoming transactions locally, so they can later be valued in USD and
reported. This feature covers only retrieving and recording incoming transactions from the
wallet. USD pricing, CSV output, and on-screen summaries are separate, later features and are
out of scope here. Behaviors: Running a sync records every incoming wallet transaction that
isn't already recorded. Running a sync again with no new transactions changes nothing. If a
sync is interrupted, already recorded transactions are kept, and the next sync records the
rest. Outgoing transactions are not recorded. If no new transactions are found, a message is
displayed to the user before the run continues. Any error encountered during the sync is
reported to the user, and the application exits. Recorded transactions persist locally
between runs. Each recorded transaction keeps its transaction id, block height, XMR amount at
full precision, and the exact moment it occurred, independent of time zone."

## Clarifications

### Session 2026-10-12

- Q: How many confirmations should an incoming transaction have before sync records it? → A:
  One. A transaction is recorded once it is included in a block; no additional
  confirmations are required.
- Q: When one transaction pays the wallet more than once (for example, to several
  subaddresses), should sync store one record or one per subaddress? → A: One record per
  transaction, with the total amount received across all subaddresses.
- Q: Should sync be a command the user runs on its own, or a step that runs automatically at
  the start of the later report commands? → A: Automatic only. Sync always runs as the first
  step of every run of the tool; there is no separate sync command.
- Q: Where can the wallet the tool connects to be running, and does the tool need to support a
  wallet that requires a username and password? → A: Any host the user specifies, including
  other machines, with optional username/password login.

### Session 2026-10-13

- Q: Are self transfers recorded as incoming transactions? → A: No. Self transfers are
  excluded when retrieving incoming transactions.
- Q: What happens on a first run when no local records exist? → A: The run creates them.
- Q: How are errors shown to the user? → A: Every error, including invalid settings and
  unreadable local records, is shown as a message with a failure status, never a raw
  traceback.
- Q: How is the wallet password supplied? → A: It can be supplied without appearing on the
  command line. A password given without a username is an error.
- Q: How does the user specify the wallet? → A: By its address (URL), not host and port.
  The URL is expected to point at the same machine (127.0.0.1 or localhost).
- Q: Can the first sync skip older transactions? → A: Yes. The first sync accepts an optional
  start date (UTC); transactions before 00:00:00 UTC on that date are not recorded. The start
  date is remembered and applied to every later sync, and a start date given on a later run
  must match the remembered one or the run fails with an error.
- Q: Which word do user-facing messages use? → A: "Transactions", never "transfers".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record incoming transactions from the wallet (Priority: P1)

A miner runs the tool, which always begins with a sync. The sync reads the wallet's incoming transactions and records each one
locally with its transaction id, block height, exact XMR amount, and the moment it occurred.
Outgoing transactions are ignored. The records remain available after the tool exits, ready
for later pricing and reporting features.

**Why this priority**: Every later feature (USD valuation, reports) depends on having an
accurate local record of incoming transactions. Without this, the tool does nothing useful.

**Independent Test**: Point the tool at a wallet containing a known mix of incoming and
outgoing transactions, run the tool, and confirm the local records contain exactly the incoming
ones with matching ids, heights, amounts, and times.

**Acceptance Scenarios**:

1. **Given** a wallet with incoming transactions and no local records, **When** the user runs
   the tool, **Then** every confirmed incoming transaction is recorded with its transaction id,
   block height, full-precision XMR amount, and time-zone-independent timestamp.
2. **Given** a wallet with both incoming and outgoing transactions, **When** the user runs the
   tool, **Then** only the incoming transactions are recorded.
3. **Given** a completed sync, **When** the tool is run again later, **Then** the previously
   recorded transactions are still present and unchanged.
4. **Given** an incoming transaction whose amount uses the wallet's full precision (12 decimal
   places), **When** it is recorded, **Then** the recorded amount equals the wallet's amount
   exactly, with no rounding.

---

### User Story 2 - Re-sync safely and incrementally (Priority: P2)

A miner runs the tool regularly (for example, daily). Each run's sync adds only transactions that
arrived since the last run. If nothing new has arrived, the tool says so and nothing in the
local records changes.

**Why this priority**: Sync is a repeated operation. It must be safe to run any number of
times without creating duplicates or altering existing records.

**Independent Test**: Run the tool, then run it again with no wallet changes and confirm the
records are identical and a "no new transactions" message appears; then add a new incoming
transaction to the wallet, sync, and confirm only that one is added.

**Acceptance Scenarios**:

1. **Given** all of the wallet's incoming transactions are already recorded, **When** the user
   runs the tool, **Then** the local records are unchanged and a message tells the user that no
   new transactions were found.
2. **Given** some incoming transactions are recorded and new ones have since arrived, **When**
   the user runs the tool, **Then** only the new transactions are added and existing records are
   unchanged.
3. **Given** no new transactions were found, **When** the message has been displayed, **Then**
   the run continues to completion rather than stopping as an error.

---

### User Story 3 - Recover from interruptions and errors (Priority: P3)

A sync is interrupted partway through (the user cancels it, the wallet becomes unreachable,
or the machine shuts down). Transactions recorded before the interruption are kept, and the
next sync records the remainder. When an error occurs, the user is told what went wrong and
the tool exits.

**Why this priority**: Interruptions are uncommon but must never corrupt or lose recorded
data, and the user must never be left believing a failed sync succeeded.

**Independent Test**: Simulate a wallet that fails partway through returning transactions;
confirm an error is reported, the tool exits with a failure status, earlier records are
intact, and a subsequent successful sync produces the same records as an uninterrupted sync.

**Acceptance Scenarios**:

1. **Given** a sync that is interrupted after recording some transactions, **When** the user
   runs the tool again, **Then** the previously recorded transactions are kept and the remaining
   incoming transactions are recorded, with no duplicates.
2. **Given** the wallet cannot be reached, **When** the user runs the tool, **Then** an error
   message describing the problem is shown, the tool exits with a failure status, and existing
   records are unchanged.
3. **Given** any error during sync, **When** the tool exits, **Then** the local records are in
   a consistent state: each transaction is either fully recorded or not recorded at all.

---

### Edge Cases

- **Unconfirmed incoming transactions** (seen by the wallet but not yet in a block): not
  recorded, because they have no block height yet; they are recorded by a later sync once
  confirmed.
- **Self transfers** (transactions the wallet sends to itself, which the wallet also reports
  as incoming): excluded when retrieving incoming transactions, so they are never recorded.
- **One transaction paying the wallet more than once** (for example, to multiple
  subaddresses): recorded once, with the total amount the wallet received in that
  transaction.
- **Previously recorded transaction reported differently by the wallet** (for example, a
  different block height after a chain reorganization): the existing record is not modified
  or deleted.
- **First run** (no local records exist yet): the tool creates the local records, then
  records the wallet's incoming transactions as on any other sync.
- **Start date given on the first sync**: incoming transactions that occurred before 00:00:00
  UTC on that date are not recorded, on this run or any later run.
- **Start date given on a later run**: accepted if it matches the start date remembered from
  the first sync; otherwise reported as an error, and nothing is recorded or changed.
- **Empty wallet** (no incoming transactions at all): treated the same as "no new
  transactions found".
- **Wallet login rejected** (wrong or missing username/password): reported as an error that
  identifies the login as the problem; the tool exits without changing existing records.
- **Password given without a username**: reported as an error; the tool does not contact the
  wallet.
- **Invalid settings** (for example, a malformed wallet address or start date): reported as
  an error; nothing is recorded or changed.
- **Wallet unreachable or not responding** (wrong address, machine offline, wallet not
  running): reported as an error that names the wallet address the tool tried to reach.
- **Local records unreadable or damaged**: reported as an error; the tool exits without
  modifying or replacing the existing records. Unreadable records are never treated as a
  first run.
- **Very large history** (thousands of incoming transactions on first sync): all are recorded
  in a single run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every run of the tool MUST begin with a sync that retrieves incoming
  transactions from the user's Monero wallet. There MUST NOT be a separate sync command; sync
  runs automatically as the first step, before any later step (such as pricing or reporting,
  delivered by later features). Until those features exist, a run consists of the sync alone.
- **FR-002**: Sync MUST record every confirmed incoming wallet transaction that is not already
  recorded, except transactions before the start date when one is set (FR-020).
- **FR-003**: Sync MUST NOT record outgoing transactions. Self transfers (transactions the
  wallet sends to itself) MUST be excluded when retrieving incoming transactions, even though
  the wallet also reports them as incoming.
- **FR-004**: Sync MUST record an incoming transaction once it is included in a block, with no
  additional confirmations required, and MUST NOT record incoming transactions that are not
  yet in a block.
- **FR-005**: Each recorded transaction MUST include its transaction id, block height, XMR
  amount, and the moment it occurred.
- **FR-006**: Recorded XMR amounts MUST be exactly equal to the amount reported by the wallet,
  to the wallet's full precision, with no rounding or approximation.
- **FR-007**: The recorded moment MUST identify a single unambiguous point in time that does
  not depend on the time zone of the machine or user.
- **FR-008**: A transaction MUST be identified by its transaction id; a transaction id that is
  already recorded MUST NOT be recorded again. When a transaction pays the wallet more than
  once (for example, to several subaddresses), it MUST be recorded as a single record whose
  amount is the total the wallet received in that transaction.
- **FR-009**: Sync MUST NOT modify or delete any existing record.
- **FR-010**: Running sync when no new incoming transactions exist MUST leave the local records
  unchanged.
- **FR-011**: When a sync finds no new incoming transactions, the tool MUST display a message
  saying so and then continue with the rest of the run.
- **FR-012**: When a sync records new transactions, the tool MUST tell the user how many were
  recorded.
- **FR-013**: If a sync is interrupted, every transaction recorded before the interruption
  MUST be kept, and no transaction MUST be left partially recorded.
- **FR-014**: A sync following an interrupted sync MUST record the remaining incoming
  transactions, so the final records match those of an uninterrupted sync.
- **FR-015**: When any error occurs during a run, including invalid settings and unreadable
  local records, the tool MUST show the user a message describing the error and exit with a
  failure status, without running any later step of the run. The tool MUST NOT show a raw
  traceback for any error.
- **FR-016**: Recorded transactions MUST persist locally between runs of the tool. When no
  local records exist, the run MUST create them. Local records that exist but cannot be read
  MUST NOT be recreated or replaced.
- **FR-017**: Users MUST be able to specify the wallet to connect to by its address (URL); the
  wallet MAY run on the same machine or on another machine.
- **FR-018**: Users MUST be able to supply an optional username and password for a wallet that
  requires login. Users MUST be able to supply the password without it appearing on the
  command line. A password supplied without a username MUST be reported as an error. The tool
  MUST NOT display the password in any output, including error messages.
- **FR-019**: User-facing messages MUST refer to "transactions", never "transfers".
- **FR-020**: On the first sync (the run that creates the local records), users MAY give an
  optional start date, interpreted in UTC. Incoming transactions that occurred before 00:00:00
  UTC on the start date MUST NOT be recorded. The start date MUST be remembered with the local
  records and applied to every later sync. A start date given on a later run MUST match the
  remembered start date; otherwise the run MUST fail with an error and change nothing.

### Key Entities

- **Incoming transaction**: A confirmed transfer of XMR into the wallet. Attributes:
  transaction id (unique identity), block height (the block that confirmed it), amount (exact
  XMR received by the wallet in this transaction), and occurred-at (the moment it occurred, as
  a time-zone-independent instant).
- **Local transaction record store**: The persistent, local collection of incoming
  transactions that survives between runs and is only ever added to by sync. It is created by
  the first run and remembers the optional start date given on the first sync.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a successful sync, 100% of the wallet's confirmed incoming transactions on
  or after the start date (all of them when no start date is set) are recorded, and 0
  outgoing transactions, self transfers, or transactions before the start date are recorded.
- **SC-002**: 100% of recorded amounts match the wallet's reported amounts exactly, to all 12
  decimal places.
- **SC-003**: Running sync any number of times in a row with no wallet changes produces
  identical records and zero duplicates.
- **SC-004**: For an interruption at any point during a sync, the records after one subsequent
  successful sync are identical to those produced by a single uninterrupted sync.
- **SC-005**: 100% of failed runs, including those caused by invalid settings or unreadable
  local records, show the user an error message and end with a failure status; no failed run
  reports success, and 0 show a raw traceback.
- **SC-006**: A sync with no new transactions, for a wallet with up to 10,000 recorded
  transactions, completes in under 5 seconds, not counting time spent waiting on the wallet.

## Assumptions

- "Incoming transactions" means all confirmed incoming transfers to the wallet, not only those
  that can be identified as mining payouts. The tool is intended for a wallet that receives
  mining income.
- The user runs a Monero wallet that the tool can reach over the network, on the same machine
  or another one. How the connection settings and login are supplied (arguments, environment,
  or a settings file) is decided during planning, within the limits of FR-018.
- A transaction's "moment it occurred" is the timestamp the wallet reports for it, at the
  precision the wallet provides (whole seconds).
- The tool works with one wallet. Supporting multiple wallets is out of scope.
- Wallet amounts have a fixed precision of 12 decimal places (the smallest Monero unit).
- USD pricing, CSV output, and on-screen income summaries are out of scope and will be
  specified as separate features.
- This feature produces no report output, so it does not create or change any golden files.
