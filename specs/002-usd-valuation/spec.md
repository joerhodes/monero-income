# Feature Specification: USD Valuation of Recorded Transactions

**Feature Branch**: `002-usd-valuation`

**Created**: 2026-10-17

**Status**: Draft

**Input**: User description: "monero-income records a Monero wallet's incoming transactions
locally (feature 001). This feature values each recorded transaction in USD. CSV output and
on-screen summaries are separate, later features and are out of scope. Behaviors: Every run,
after a successful sync, looks up the USD price for each UTC calendar day that has recorded
transactions but no price yet. Each transaction is valued at the USD price for its UTC
calendar day; all transactions on the same day share that day's price. Prices and USD values
are kept at full precision; rounding happens only on output. Once a day's price is recorded,
it is not changed. If the lookup is interrupted, prices already recorded are kept, and the
next run looks up the rest. If the price source is unavailable or rate-limits the run, prices
already recorded are kept, the run reports how many days still lack a price, and the next run
continues. The run does not fail. The tool paces its requests to stay within the price
source's limits. The price source only provides history for a limited recent period. A day
older than that period is not requested; its transactions remain unvalued, and the run
reports such days separately from temporary failures. The user may supply an API key for the
price source. It is never shown in any output. P3 (optional): the user can import daily USD
prices from a previous xmr-income-report database. Imported prices fill in days that have no
price yet and never replace a recorded price."

## Clarifications

### Session 2026-10-17

- Q: Should the tool record a price for the current, incomplete UTC day? → A: Option C. Prices
  for recent days are provisional: a day's price stays provisional until the day has settled
  (a settling period after the day ends), is refreshed while provisional, and is then
  finalized. The tool does not run every day, so finalization depends on a lookup made after
  the day has settled, not on how much time has passed: a provisional price is never
  finalized without such a lookup.
- Q: What is a day's price? → A: The price source's daily price for that UTC calendar date.
  (Replaces the assumption that it matches the original tool's definition, which can't be
  verified here.)
- Q: How long is the settling period? → A: 1 hour after the end of the UTC day. The source
  documents that a completed UTC day's data is published about 35 minutes after midnight UTC.
  Planning may confirm the value.
- Q: What happens when the price source rate-limits the run? → A: After a brief retry, the run
  stops looking up prices for the rest of the run; it doesn't keep requesting later days.
- Q: In what order are days looked up? → A: Oldest first, so days nearest the end of the
  history period are priced before they age out.
- Q: What happens on an error during pricing that isn't a price-source problem (for example, a
  storage error)? → A: The run ends with a message and a failure status, as in feature 001.
  Only price-source problems leave the run successful.
- Q: How should the user start the optional price import from an xmr-income-report database?
  → A: An option on the normal run (for example `--import-prices PATH`). The run syncs,
  imports prices from the file, then looks up whatever is still missing.
- Q: When this run couldn't refresh a day that already has a provisional price, how should that
  day show up in the run's report? → A: As a separate count from days with no price, for
  example "2 days still have no price; 1 provisional price couldn't be refreshed".
- Q: How long may a first run take when it has to price a full year of days? → A: Under 5
  minutes.
- Q: What does the optional import read, and which days may it fill? → A: A CSV file with a
  header row and two columns, `date_utc` (YYYY-MM-DD) and `usd_price` (USD per 1 XMR), not a
  previous database (supersedes the earlier "previous xmr-income-report database" wording).
  Imported prices are recorded, as final, only for days older than the price source's
  history period that have no recorded price; days inside the period are always priced by the
  source. A file with any invalid row (bad date, missing or non-positive price, duplicate
  date) is rejected as a whole, and the error names the first bad row. Rows for days that
  already have a price or are inside the history period are skipped and counted in the run's
  report. The import is requested with an option on the main command, and the run then
  continues as normal.
- Q: The keyless price-source tier is too slow to price a full year in under 5 minutes without
  rate-limit refusals; how should SC-012 change? → A: SC-012 applies when an API key is
  configured.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Value recorded transactions in USD (Priority: P1)

A miner runs the tool. After the sync records any new incoming transactions, the tool finds
every UTC calendar day that has recorded transactions but no USD price yet, looks up that
day's price, and records it. Every transaction on that day is then valued at that price: its
exact XMR amount times the day's USD price, at full precision. A recent day's price is
provisional at first and is refreshed by later runs until the day has settled; then it is
finalized and never looked up again.

**Why this priority**: USD valuation is the point of the tool: weekly and monthly income
reports (later features) need a USD value for every transaction. Without prices, recorded
transactions can't be reported in USD.

**Independent Test**: With recorded transactions on three different UTC days and a price
source that answers for all three, run the tool. Each day gets exactly one price, and each
transaction's USD value equals its XMR amount times its day's price, with no rounding.

**Acceptance Scenarios**:

1. **Given** recorded transactions on days that have no price, **When** the user runs the
   tool and the sync succeeds, **Then** the tool records a USD price for each of those days.
2. **Given** two transactions on the same UTC day, **When** prices are recorded, **Then** both
   are valued at that one day's price.
3. **Given** a transaction of 1.234567890123 XMR on a day priced at 152.3456 USD, **When** it
   is valued, **Then** its USD value is exactly 188.0809859615225088, with no rounding until
   output.
4. **Given** a day that already has a final price, **When** the user runs the tool again,
   **Then** that day's price isn't looked up again and isn't changed.
5. **Given** the sync fails, **When** the run ends, **Then** no prices are looked up (the run
   stops at the sync error, as in feature 001).
6. **Given** every day with transactions already has a final price, **When** the user runs the
   tool, **Then** no lookups are made and the run says all transactions are valued.
7. **Given** transactions today (UTC), **When** the user runs the tool, **Then** today gets a
   provisional price and its transactions are valued at it.
8. **Given** a day with a provisional price that has not settled yet, **When** the user runs
   the tool, **Then** the day is looked up again, its provisional price is replaced by the new
   one, and it stays provisional.
9. **Given** a day with a provisional price that has since settled, **When** the user runs the
   tool, even many days later, **Then** the day is looked up once more and the price from
   that lookup is recorded as final.

---

### User Story 2 - Keep going through interruptions, outages, and rate limits (Priority: P2)

The price source is a third-party service that can be slow, unavailable, or refuse requests
when called too often. The tool paces its requests to stay within the source's limits. If a
run is interrupted, or the source fails or rate-limits it partway through, every price
already recorded is kept. The run still completes successfully: it reports how many days
still lack a price, and a later run picks up the rest.

**Why this priority**: A first run may need prices for many days. Without pacing and
graceful handling, one failure would waste the work already done or make the whole run fail
for a problem the user can't fix.

**Independent Test**: With ten unpriced days and a price source that fails after answering
four, run the tool. Four prices are recorded, the run completes successfully and reports
six days still lacking a price, and the next run (source available) records the other six
without re-requesting the first four.

**Acceptance Scenarios**:

1. **Given** the price source becomes unavailable after some days were priced, **When** the
   run ends, **Then** the prices already recorded are kept, the run reports how many days
   still lack a price, and the run ends successfully.
2. **Given** the price source rate-limits the run, **When** a brief retry is also refused,
   **Then** the run makes no further price requests, and the same applies: prices kept,
   remaining days reported, run successful.
3. **Given** a run is interrupted (for example, the user cancels it) during price lookups,
   **When** the user runs the tool again, **Then** the prices recorded before the
   interruption are kept, and only the days still lacking a final price are looked up.
4. **Given** many days need prices, **When** the tool looks them up, **Then** it spaces its
   requests so that it stays within the price source's published limits.
5. **Given** the price source is unreachable from the start, **When** the run ends, **Then**
   the sync's results are still reported, the run reports the days lacking a price, and the
   run ends successfully.
6. **Given** several days need prices and the run stops early, **When** the run ends, **Then**
   every day it priced is older than every day it left unpriced.
7. **Given** an error during pricing that isn't a price-source problem (for example, the
   database can't be written), **When** the run ends, **Then** it shows an error message and
   ends with a failure status, and prices recorded before the error are kept.

---

### User Story 3 - Days older than the price history (Priority: P2)

The price source only provides history for a limited recent period. A day older than that
period is never requested. Its transactions stay unvalued, and the run reports these days
separately from days that failed temporarily, so the user knows a retry won't help.

**Why this priority**: A user setting up the tool for a wallet with a long history will have
old days the source can't price. Treating them as temporary failures would make every run
retry requests that can never succeed, and would hide the real situation from the user.

**Independent Test**: With unpriced days both inside and outside the source's history period,
run the tool. Only the days inside the period are requested, and the run reports the old days
as a separate count from any days that failed temporarily.

**Acceptance Scenarios**:

1. **Given** an unpriced day older than the source's history period, **When** the user runs the
   tool, **Then** no request is made for that day and its transactions remain unvalued.
2. **Given** both old days and temporarily failed days, **When** the run ends, **Then** the run
   reports the two counts separately, and makes clear that old days won't be priced by a
   later run.

---

### User Story 4 - Import prices from a CSV file (Priority: P3, optional)

A user has daily USD prices from elsewhere (for example, exported from the earlier
xmr-income-report tool) for days older than the price source's history, which the source can
no longer price. They run the tool as usual, adding an option that names a CSV file of daily
prices. After the sync, the run imports prices for those old days, then continues as normal,
looking up prices from the source. Imported prices only fill in old days that have no price;
days inside the history period are always priced by the source, and a recorded price is never
replaced.

**Why this priority**: Optional. It recovers valuations the price source can no longer
provide, but the core feature works without it.

**Independent Test**: With a CSV file of five rows (two old days with no price, one old day
that already has a price, and two days inside the history period), run the tool with the
import option. The two old unpriced days get the imported prices, recorded as final; the
other three rows are skipped and counted in the run's report; the existing price is
unchanged; and the two recent days are priced by the source.

**Acceptance Scenarios**:

1. **Given** a CSV file with rows for days older than the history period that have no price,
   **When** the user runs the tool with the import option, **Then** those days get the
   imported prices, recorded as final.
2. **Given** a row for a day that already has a recorded price, **When** the user imports the
   file, **Then** the row is skipped, the recorded price is not changed, and the row is counted
   as skipped in the run's report.
3. **Given** a row for a day inside the history period, **When** the user imports the file,
   **Then** the row is skipped and counted as skipped, and that day is priced by the source.
4. **Given** a file with any invalid row (a bad date, a missing or non-positive price, or a
   date that appears twice), **When** the user tries to import it, **Then** the whole file is
   rejected, no imported prices are recorded, the error names the first bad row, the file is
   left unchanged, and the run ends with a failure status before any price lookups.
5. **Given** an import has run, **When** the user imports the same file again, **Then** nothing
   new is recorded; every row is skipped and counted.
6. **Given** a run with the import option, **When** the sync fails, **Then** nothing is imported
   and no prices are looked up.

---

### Edge Cases

- **Current UTC day** (not yet over): priced provisionally, like any day that hasn't settled.
- **Tool not run for a long time**: a provisional price recorded before the gap is refreshed by
  the next run and finalized then, because the day has settled; it is never finalized just
  because time has passed.
- **Refreshing a provisional price fails** (source unavailable, rate-limited): the provisional
  price is kept, transactions stay valued at it, the run reports it in a separate count of
  provisional prices it couldn't refresh (not among days with no price), and the day is
  retried on a later run.
- **Provisional day falls out of the history period before it can be refreshed** (the tool
  wasn't run for longer than the history period): no request is made, the price stays
  provisional, and the run counts the day with the days older than the history period.
- **Day first priced after it has settled** (for example, a transaction recorded weeks after it
  happened): the price is recorded as final straight away.
- **Day with transactions but the source has no price for it** (inside the history period):
  treated as a temporary failure; the day is reported as lacking a price and retried on a
  later run.
- **Price source returns a malformed or impossible price** (missing, zero, negative): not
  recorded; the day counts as lacking a price.
- **API key rejected by the price source**: prices aren't recorded for the remaining days, the
  run reports that the key was rejected (without showing the key) and how many days lack a
  price, and the run ends successfully.
- **No API key supplied**: the tool uses the price source without a key, within the limits
  that apply to unauthenticated use.
- **Day exactly at the edge of the history period**: inside the period means requested; the
  boundary follows the source's published limit.
- **Transaction recorded on a day that was already priced** (a later sync records another
  transaction for a priced day): it's valued at the existing price; a final price is not
  looked up again.
- **Second run started while one is pricing**: the second run may fail with a storage error,
  and no recorded price is lost (as with feature 001's sync).
- **Rate limit during a run**: one brief retry; if that is refused too, no more price requests
  are made in that run, and the remaining days are reported as lacking a price.
- **Days close to the end of the history period**: because days are looked up oldest first,
  they are priced before more recent days, so a run that stops early doesn't leave them to
  age out.
- **Storage error during pricing**: the run fails with an error message and a failure status,
  as in feature 001; prices recorded before the error are kept.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every run MUST, after a successful sync, look up the USD price for each UTC
  calendar day that has at least one recorded transaction and either no recorded price or a
  provisional one.
- **FR-002**: When the sync fails, the run MUST NOT look up prices.
- **FR-003**: Each recorded price MUST be the price source's daily USD price for one UTC
  calendar date. All transactions on that day MUST be valued at that day's price.
- **FR-004**: A transaction's USD value MUST equal its exact XMR amount multiplied by its day's
  USD price, with no rounding or approximation before output.
- **FR-005**: Recorded prices MUST keep the full precision the price source provides.
- **FR-006**: Once a day's price is final, it MUST NOT be changed or deleted, by a later run or
  by an import.
- **FR-007**: A day that already has a final price MUST NOT be looked up again.
- **FR-008**: If price lookups are interrupted, every price recorded before the interruption
  MUST be kept, and the next run MUST look up only the days still lacking a final price.
- **FR-009**: If the price source is unavailable, rejects the request, or rate-limits the run
  (after a brief retry), the run MUST keep every price already recorded, make no further price
  requests in that run, report how many days still have no price and, separately, how many
  provisional prices it couldn't refresh, and end successfully.
- **FR-010**: The tool MUST pace its requests to stay within the price source's published
  request limits.
- **FR-011**: A day older than the price source's history period MUST NOT be requested; its
  transactions MUST remain unvalued.
- **FR-012**: The run MUST report the number of days older than the history period separately
  from the number of days that have no price for temporary reasons, and separately from the
  number of provisional prices it couldn't refresh.
- **FR-013**: When prices were recorded, the run MUST report how many days were priced and how
  many of those prices are provisional.
- **FR-014**: When every day with recorded transactions has a final price, the run MUST say
  that all transactions are valued.
- **FR-015**: Users MUST be able to supply an optional API key for the price source, without it
  appearing on the command line. The key MUST NOT appear in any output, including error
  messages and warnings.
- **FR-016**: A price the source returns that is missing, zero, or negative MUST NOT be
  recorded; the day counts as lacking a price.
- **FR-017**: Recorded prices MUST persist locally between runs, alongside the recorded
  transactions.
- **FR-018**: User-facing messages MUST refer to "transactions", never "transfers" (as in
  feature 001).
- **FR-019** *(P3, optional)*: Users MUST be able to import daily USD prices from a CSV file by
  naming it with an option on the main command (no separate command). The file MUST have a
  header row and two columns: `date_utc` (a UTC date, YYYY-MM-DD) and `usd_price` (USD per 1
  XMR). The run MUST import after a successful sync and before any price lookups, then
  continue as normal. An imported price MUST be recorded only for a day that is older than the
  price source's history period and has no recorded price, and MUST be recorded as final.
  Rows for days that already have a price (provisional or final) or are inside the history
  period MUST be skipped, never replacing a recorded price; the run MUST report how many
  prices were imported and how many rows were skipped. Without the option, no import happens.
- **FR-020** *(P3, optional)*: A file with any invalid row (a date that isn't a valid
  YYYY-MM-DD, a missing or non-positive price, or a date that appears more than once), a
  missing or wrong header, or a file that can't be read MUST be rejected as a whole: no
  imported price is recorded, the file is left unchanged, the error names the first bad row
  (or the header or file problem), and the run ends with a failure status before any price
  lookups (FR-025). Importing the same file twice MUST record nothing the second time.
- **FR-021**: A day is *settled* once its settling period (1 hour) after the end of the UTC
  day has passed. A price looked up before the day has settled MUST be recorded as provisional; a
  price looked up after the day has settled MUST be recorded as final.
- **FR-022**: A provisional price MUST be replaced only by a newer looked-up price for the same
  day. It MUST become final only through a lookup made after the day has settled, never
  because time has passed without a lookup.
- **FR-023**: A failed lookup MUST NOT remove or change a provisional price; transactions on
  that day MUST stay valued at it.
- **FR-024**: Days MUST be looked up in date order, oldest first.
- **FR-025**: An error during pricing that isn't a price-source problem (for example, a storage
  error) MUST end the run with a message describing the error and a failure status, as in
  feature 001 FR-015. Prices recorded before the error MUST be kept.

### Key Entities

- **Daily price**: The USD price of 1 XMR for one UTC calendar day. Attributes: the UTC date
  (unique), the price at full precision, its status (provisional or final), and where it came
  from (the price source, or an import). At most one per day. A provisional price may be
  replaced by a newer lookup; a final price is never changed.
- **Transaction valuation**: A recorded transaction's USD value: its exact XMR amount times its
  day's price. It exists only for transactions whose day has a price, and is provisional or
  final with that price.
- **Incoming transaction** (from feature 001): gains no new attributes. Its UTC calendar date
  links it to a daily price.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a run in which the price source answers every request, 100% of days with
  recorded transactions inside the source's history period have a price, 100% of settled days
  among them have a final price, and 100% of those transactions have a USD value.
- **SC-002**: 100% of USD values equal the exact product of XMR amount and day price, with no
  rounding before output.
- **SC-003**: 0 final prices change across any number of later runs or imports.
- **SC-004**: When the price source fails or rate-limits a run, 100% of prices recorded before
  the failure are kept, and the run ends successfully.
- **SC-005**: After any interruption or temporary failure, the next run that completes without
  failure leaves the same prices as a single uninterrupted run.
- **SC-006**: 0 requests are made for days older than the source's history period.
- **SC-007**: Under normal conditions, a run pricing up to a full history period of days
  receives 0 rate-limit refusals from the price source.
- **SC-008**: The API key appears in 0 lines of output.
- **SC-009**: 0 provisional prices become final without a lookup made after their day settled,
  however long the tool goes without running.
- **SC-010**: In 100% of runs that stop pricing early, every day priced is older than every day
  left unpriced.
- **SC-011**: After a rate limit that a brief retry doesn't clear, the run makes 0 further price
  requests.
- **SC-012**: With an API key configured, under normal conditions, the pricing step of a first
  run that must price a full year of days (365) finishes in under 5 minutes, not counting the
  sync, while still meeting SC-007 (0 rate-limit refusals).

## Assumptions

- The price source is a third-party web service that reports a daily USD price for XMR,
  limits how often it may be called, and only provides history for a limited recent period
  (for example, the last 365 days without a paid plan). The exact service, its limits, and
  its history period are chosen during planning, along with a lookup method (for example,
  several days per request) that meets SC-012 within those limits.
- A day's price is the price source's daily price for that UTC calendar date.
- The settling period is 1 hour after the end of the UTC day: the source documents that a
  completed UTC day's data is published about 35 minutes after midnight UTC. Planning may
  confirm the value.
- How the API key is supplied (for example, the config file, as with the wallet password) is
  decided during planning, within the limits of FR-015.
- "Temporary failure" covers the source being unreachable, timing out, answering with an
  error, rate-limiting, or rejecting the API key. All are retried on a later run.
- Valuing a transaction doesn't change its recorded data (feature 001 FR-009 still holds).
- A price-source problem (failed or partial lookups) doesn't change the run's exit status: the
  run succeeds if the sync succeeded. Other errors during pricing fail the run (FR-025).
- Feature 001's messages and behavior are unchanged; this feature adds lines after the sync's
  line.
- This feature produces no report output (CSV or summaries), so it creates or changes no
  golden files.
