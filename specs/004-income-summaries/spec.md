# Feature Specification: On-Screen Income Summaries

**Feature Branch**: `004-income-summaries`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "monero-income records a Monero wallet's incoming transactions
(feature 001), values them in USD (feature 002), and exports them to a CSV file (feature 003).
This feature displays income summaries on screen, giving the user an at-a-glance view of
recent income by week, month, and year. The monthly summary CSV and Configurable ranges are
out of scope. Behaviors: Every run that completes sync, pricing, and export displays three
summaries: the last 26 weeks, the last 12 months, and the last 4 years, each including the
current, partial period. Periods are calendar periods in the local time zone (the machine's by
default, or the configured one): ISO weeks (labeled YYYY-Www), months (YYYY-MM), and years
(YYYY). Periods with no transactions are shown with zero values. Rows are ordered oldest
first. Each summary has columns Period, XMR (12 decimal places), and USD (rounded to the cent,
half-cents away from zero, with thousand separators), and a final total row covering only the
periods shown. Totals are summed at full precision and rounded once. A transaction without a
price adds its XMR but nothing to USD. A USD value that includes a provisional price, or that
excludes an unpriced transaction, is marked, with a short legend explaining the marks. Layout:
when the terminal is wide enough, the weekly summary appears on the left, with the monthly and
annual summaries stacked to its right. When the terminal is too narrow, or the output is not a
terminal, the summaries are printed one after another: weekly, monthly, annual. With no
recorded transactions, a single message replaces the summaries."

## Clarifications

### Session 2026-10-27

- Q: How are USD values written on screen? → A: With a dollar sign before the amount, for
  example `$1,234,567.90`.
- Q: Should the summary time zone also be settable with a command-line option, or only in
  the configuration file? → A: Both: a configuration file setting and a command-line option;
  the option wins, then the file, then the machine's local time zone (as with
  `--reports-path`).
- Q: Should XMR figures in the summaries use thousand separators like USD? → A: Yes, for
  example `1,234.500000000000`; the 12 decimal places are not grouped.
- Q: If the run writes the export but then can't read the recorded data for the summaries,
  should it still print the sync, pricing, and export lines before the error? → A: Yes: it
  prints those lines, then the error, and ends with a failure status.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See recent income by week, month, and year after each run (Priority: P1)

A miner runs the tool as usual. After the sync, pricing, and export lines, the run shows three
tables: the last 26 weeks, the last 12 months, and the last 4 years, each ending with the
current, partial period. Each table lists its periods oldest first with the XMR received and
its USD value, including periods with no income, and ends with a total row. Weeks, months,
and years follow the calendar in the user's local time zone, so a payout received late on
Sunday evening counts in that week, as the user would expect.

**Why this priority**: This is the feature. Today the user sees how many transactions were
recorded and priced, but not how much they earned; answering "what did I make this month?"
means opening the export in a spreadsheet.

**Independent Test**: With transactions recorded in three different weeks of the current
month and one transaction two years ago, all on final-priced days, run the tool with output
redirected to a file. The output ends with a weekly table of 26 rows plus a total, a monthly
table of 12 rows plus a total, and an annual table of 4 rows plus a total, in that order. Each
row's XMR and USD match the sum of that period's transactions, empty periods show zero, and
each total matches the sum of the periods shown.

**Acceptance Scenarios**:

1. **Given** recorded transactions, **When** a run completes its sync, pricing, and export,
   **Then** the output, after the export line, shows a weekly, a monthly, and an annual
   summary.
2. **Given** today is in ISO week 2026-W44, **When** the weekly summary is shown, **Then** its
   rows are 2026-W19 through 2026-W44, oldest first: 26 rows, the last being the current week.
3. **Given** today is 2026-10-27, **When** the monthly and annual summaries are shown, **Then**
   the monthly rows are 2025-11 through 2026-10 and the annual rows are 2023 through 2026,
   oldest first.
4. **Given** a period in range with no transactions, **When** the summaries are shown, **Then**
   that period's row shows `0.000000000000` XMR and `$0.00` USD.
5. **Given** a month with transactions of 1.5 XMR at a final price of 150.00 USD and
   0.25 XMR at a final price of 160.004 USD, **When** the monthly summary is shown, **Then**
   that month's XMR is `1.750000000000` and its USD is `$265.00` (225 + 40.001 = 265.001,
   rounded once).
6. **Given** a period whose USD value is 1234567.895 exactly, **When** the summary is shown,
   **Then** its USD reads `$1,234,567.90`.
7. **Given** transactions recorded before the oldest period shown, **When** the summaries are
   shown, **Then** those transactions appear in no row and in no total.
8. **Given** each summary, **When** it is shown, **Then** its last row is a total of the XMR
   and of the USD over exactly the periods shown, with the USD summed at full precision and
   rounded once.
9. **Given** the local time zone is America/New_York, **When** the summaries are shown,
   **Then** a transaction at 2026-11-01T03:30:00Z (Saturday 2026-10-31 23:30 local) counts in
   month 2026-10, not 2026-11, and a transaction at 2026-10-26T03:30:00Z (Sunday 2026-10-25
   23:30 local) counts in week 2026-W43, not 2026-W44.
10. **Given** no transactions are recorded, **When** a run completes, **Then** a single
    message saying there are no transactions to summarize is shown instead of the three
    summaries.
11. **Given** the sync, pricing, or export fails, **When** the run ends, **Then** no summary
    is shown.

---

### User Story 2 - Know which figures are incomplete or may change (Priority: P2)

Some days are priced provisionally and some have no price yet (feature 002). The summaries
mark every USD figure that includes a provisional price, so may still change, and every USD
figure that leaves out a transaction with no price, so is too low. A short legend under the
summaries explains each mark that appears.

**Why this priority**: Without the marks, an unpriced transaction silently shrinks a period's
USD and a provisional figure looks settled. The summaries are still useful without the marks,
but they could mislead.

**Independent Test**: Record transactions in the current week on a provisionally priced day,
in the previous week on an unpriced day, and in an earlier week on a final-priced day. Run
the tool. The current week's USD carries the provisional mark, the previous week's carries the
unpriced mark, the earlier week's carries neither, the totals carry both marks, and the legend
explains both.

**Acceptance Scenarios**:

1. **Given** a period containing a transaction valued at a provisional price, **When** the
   summary is shown, **Then** that period's USD carries the provisional mark.
2. **Given** a period containing a transaction whose day has no price, **When** the summary is
   shown, **Then** that period's XMR includes the transaction, its USD doesn't, and its USD
   carries the unpriced mark.
3. **Given** a period with both a provisionally priced and an unpriced transaction, **When**
   the summary is shown, **Then** its USD carries both marks.
4. **Given** a period whose transactions are all unpriced, **When** the summary is shown,
   **Then** its USD is `$0.00` with the unpriced mark.
5. **Given** any period in a summary carries a mark, **When** the summary is shown, **Then**
   that summary's total USD carries the same mark.
6. **Given** a mark appears anywhere in the summaries, **When** they are shown, **Then** a
   legend explains that mark; marks that don't appear aren't listed in the legend, and with
   no marks there is no legend.
7. **Given** all transactions in the periods shown are on final-priced days, **When** the
   summaries are shown, **Then** no USD figure carries a mark.

---

### User Story 3 - See all three summaries at once on a wide terminal (Priority: P2)

On a terminal wide enough, the weekly summary appears on the left and the monthly and annual
summaries are stacked to its right, so all three fit on one screen. On a narrow terminal, or
when the output is redirected to a file or another program, the summaries are printed one
after another: weekly, monthly, annual.

**Why this priority**: The weekly table alone is 26 rows; printed one after another, the three
tables scroll the start of the run's output off a typical screen. The side-by-side layout is a
convenience; the figures are the same either way.

**Independent Test**: Run the tool in a terminal wide enough for the side-by-side layout, then
in a narrow one, then with output redirected to a file. The first shows weekly on the left and
monthly above annual on the right; the other two show the three summaries one after another,
and every figure is the same in all three runs.

**Acceptance Scenarios**:

1. **Given** the output is a terminal at least as wide as the side-by-side layout, **When** the
   summaries are shown, **Then** the weekly summary is on the left and the monthly summary
   above the annual summary on the right:

   ```text
   +---------+-----------------+
   | Weekly  | Monthly Summary |
   | Summary | Annual Summary  |
   +---------+-----------------+
   ```

2. **Given** the output is a terminal narrower than the side-by-side layout, **When** the
   summaries are shown, **Then** they are printed one after another: weekly, monthly, annual.
3. **Given** the output is not a terminal (redirected to a file or another program), **When**
   the summaries are shown, **Then** they are printed one after another, whatever the width.
4. **Given** either layout, **When** the summaries are shown, **Then** no line is wider than
   the layout it uses, and in the side-by-side layout no line is wider than the terminal.
5. **Given** the same recorded data and the same day, **When** the summaries are shown in
   either layout, **Then** every period, figure, mark, and the legend are identical.

---

### User Story 4 - Use a time zone other than the machine's (Priority: P3)

By default, periods follow the machine's local time zone. The user can set another time zone
in the configuration file, or for a single run with a command-line option, for example when
the machine runs in UTC but the user's income is counted in their home time zone.

**Why this priority**: Most users run the tool on their own machine, already set to their
time zone. The setting matters for servers and for users who keep accounts in a different
zone.

**Independent Test**: With a transaction at 2026-11-01T03:30:00Z, run the tool on a machine
set to UTC, first with no time zone setting (the transaction counts in 2026-11), then with the
time zone set to America/New_York in the configuration file (it counts in 2026-10), then with
the file's setting still there and the command-line option set to UTC (it counts in
2026-11).

**Acceptance Scenarios**:

1. **Given** no time zone setting, **When** the summaries are shown, **Then** periods follow
   the machine's local time zone.
2. **Given** a time zone set in the configuration file, **When** the summaries are shown,
   **Then** periods, and the current period, follow that time zone.
3. **Given** a time zone set both in the configuration file and with the command-line option,
   **When** the summaries are shown, **Then** the option's time zone is used.
4. **Given** a time zone setting, in the file or the option, that isn't a text value, is empty,
   or isn't a known time zone name, **When** the run starts, **Then** it shows an error naming
   the setting and ends with a failure status before syncing, as with other invalid
   configuration (feature 001).

---

### Edge Cases

- **No transactions recorded**: a single message replaces the three summaries.
- **Transactions only before the oldest period shown**: the summaries are shown with every
  period at zero and zero totals; the message for no transactions is not used.
- **Current period**: always the last row of each summary, even when it has no transactions
  yet; its figures cover only the part of the period so far.
- **ISO week years**: a week is labeled with its ISO week-numbering year, which can differ
  from the calendar year near 1 January (for example, 2026-12-31 is in 2026-W53, and
  2027-01-01 is in 2026-W53 too). Years with 53 ISO weeks are handled; the weekly summary is
  always the 26 consecutive weeks ending with the current one.
- **Weekly summary crossing a year boundary**: its rows run continuously from one ISO year
  into the next (for example, 2026-W45 … 2026-W53, 2027-W01 …).
- **Week split across months or years**: a week is one row in the weekly summary; its
  transactions count in the month and year of each transaction's own local date.
- **Transaction near local midnight**: its period is its local date, while its USD price
  remains the price of its UTC day (feature 002). For example, a transaction at
  2026-10-31 23:30 in New York (2026-11-01 03:30 UTC) is counted in October at the
  2026-11-01 price.
- **Daylight saving changes**: periods follow local calendar dates, so a week or month that
  includes a clock change is still one period.
- **Transaction dated after the current period** (for example, the machine's clock is behind):
  it appears in no row and no total.
- **USD exactly halfway between two cents**: rounded away from zero, so `0.125` becomes
  `$0.13` (all values are positive, so this is the same as feature 003's half up).
- **Totals versus rows**: the total is the exact sum rounded once, so it can differ by a cent
  or so from adding the rounded rows by hand.
- **Large values**: USD and XMR both use thousand separators in the whole part
  (`$1,234,567.90`, `1,234.500000000000`); XMR shows exactly 12 decimal places, ungrouped.
- **Provisional price later finalized**: the next run's summaries use the final price and drop
  the provisional mark for periods with no other provisional price.
- **Day older than the price history with no imported price**: its transactions are unpriced
  and marked, like any other unpriced transaction.
- **Terminal too narrow even for one summary**: the summaries are printed one after another
  as usual; lines may wrap, but no figure is shortened or dropped.
- **Run fails before the summaries** (invalid configuration, sync failure, storage error
  during pricing, export write failure): no summary is shown, as no export line is shown.
- **Recorded data can't be read for the summaries** (after the export was written): the run
  prints the sync, pricing, and export lines, then an error, and ends with a failure status;
  the export already written stays.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every run that completes its sync, pricing, and export MUST display three
  summaries after the export line (feature 003 FR-021): weekly, monthly, and annual. A run that
  fails before then MUST NOT display any summary.
- **FR-002**: The weekly summary MUST cover the 26 consecutive ISO weeks ending with the
  current week; the monthly summary the 12 consecutive calendar months ending with the current
  month; and the annual summary the 4 consecutive calendar years ending with the current year.
- **FR-003**: Periods MUST be calendar periods in the summary time zone: ISO 8601 weeks
  (Monday to Sunday) labeled `YYYY-Www` with the ISO week-numbering year (for example,
  `2026-W07`), months labeled `YYYY-MM`, and years labeled `YYYY`. The current period is the
  one containing the run's current moment in that time zone.
- **FR-004**: Each transaction MUST be counted in the period containing its recorded moment
  converted to the summary time zone.
- **FR-005**: The summary time zone MUST be, in order of precedence: the command-line option,
  then the configuration file setting, then the machine's local time zone.
- **FR-006**: An invalid time zone setting, from the option or the file (not a text value,
  empty, or not a known time zone name), MUST be reported as an error naming the setting, and
  the run MUST end with a failure status before syncing, as for other invalid configuration
  (feature 001).
- **FR-007**: Each summary MUST list every period in its range, oldest first, including
  periods with no transactions, which MUST show zero XMR and zero USD.
- **FR-008**: Each summary MUST have the columns Period, XMR, and USD, in that order, with a
  title naming the summary (weekly, monthly, or annual).
- **FR-009**: A period's XMR MUST be the exact sum of the amounts of all its transactions,
  priced or not, shown with exactly 12 decimal places and thousand separators in the whole
  part (for example, `1,234.500000000000`).
- **FR-010**: A period's USD MUST be the exact sum of the USD values (amount times its UTC
  day's recorded price, feature 002) of its priced transactions, rounded once to the nearest
  cent, half a cent away from zero, and shown with a leading dollar sign, exactly 2 decimal
  places, and thousand separators (for example, `$1,234,567.90`). Transactions with no price
  MUST add nothing to USD.
- **FR-011**: Each summary MUST end with a total row whose XMR is the exact sum over the
  periods shown and whose USD is the exact sum over the periods shown, rounded once as in
  FR-010. Transactions outside the periods shown MUST NOT count in the total.
- **FR-012**: A USD figure (period or total) MUST carry a provisional mark when it includes at
  least one transaction valued at a provisional price, and an unpriced mark when it leaves out
  at least one transaction whose day has no price. Both marks MUST appear when both apply.
- **FR-013**: When any mark appears in the summaries, a short legend MUST be shown after them
  explaining each mark that appears, and only those.
- **FR-014**: When the output is a terminal at least as wide as the side-by-side layout, the
  weekly summary MUST be shown on the left with the monthly summary above the annual summary
  on its right. Otherwise (a narrower terminal, or output that isn't a terminal), the summaries
  MUST be shown one after another: weekly, monthly, annual.
- **FR-015**: The periods, figures, marks, and legend MUST be the same in both layouts.
- **FR-016**: When no transactions are recorded, a single message saying there are no
  transactions to summarize MUST be shown instead of the summaries and legend.
- **FR-017**: Displaying the summaries MUST NOT change any recorded transaction or price, or
  the export.
- **FR-018**: If the recorded transactions and prices can't be read for the summaries, the run
  MUST still print feature 001, 002, and 003's lines, including the export line, then show an
  error and end with a failure status; no summary is shown, and the export already written
  MUST be left as it is.
- **FR-019**: The summaries MUST reflect the recorded transactions and prices as they stand at
  the end of the run's pricing (and import, if any), the same data as the run's export.
- **FR-020**: Feature 001, 002, and 003's output lines MUST be unchanged; the summaries (or the
  no-transactions message) and the legend MUST be the only additions to a successful run's
  output.
- **FR-021**: User-facing text MUST refer to "transactions", never "transfers" (as in features
  001 to 003).

### Key Entities

- **Summary period**: One ISO week, calendar month, or calendar year in the summary time zone.
  Attributes: label, total XMR, total USD (exact), whether it includes a provisional price,
  whether it leaves out an unpriced transaction.
- **Summary**: The weekly (26 periods), monthly (12), or annual (4) table ending with the
  current period, oldest first, with a total row over its periods.
- **Summary time zone**: Set by command-line option, then the configuration file, then the
  machine's local time zone. Decides each transaction's period and which period is current. It
  doesn't change which day's price a transaction is valued at; that remains its UTC day
  (feature 002).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After 100% of runs that complete sync, pricing, and export, the output shows the
  three summaries (or, with no transactions, the single message).
- **SC-002**: For 100% of periods shown, XMR equals the exact sum of the period's transaction
  amounts, and USD differs from the exact sum of its priced transactions' values by at most
  half a cent.
- **SC-003**: For 100% of totals, USD differs from the exact sum over the periods shown by at
  most half a cent, and XMR equals that sum exactly.
- **SC-004**: 100% of USD figures that include a provisional price or leave out an unpriced
  transaction are marked, and 0 others are.
- **SC-005**: For the same recorded data, day, and time zone, both layouts show identical
  periods, figures, marks, and legend.
- **SC-006**: On a terminal wide enough for the side-by-side layout, all three summaries fit
  within 40 lines.
- **SC-007**: With 100,000 recorded transactions, showing the summaries adds less than one
  second to the run.

## Assumptions

- **Time zone setting**: no time zone setting exists yet, so this feature adds a configuration
  file setting and a command-line option, both taking an IANA time zone name (for example,
  `America/New_York`). Planning names the key and the option.
- **Marks and legend wording**: the exact mark characters and legend text are set in planning
  and locked by golden-file tests. The marks are plain ASCII so they show in any terminal and
  in redirected output.
- **Number format**: USD starts with `$` and uses `,` as the thousand separator and `.` as the
  decimal point, whatever the machine's locale. XMR uses the same separators in its whole part,
  and its 12 decimal places are not grouped. Figures are right-aligned so the decimal points
  line up.
- **Rounding**: "half a cent away from zero" equals feature 003's "half up", since every value
  is zero or positive.
- **Which price applies**: a transaction's USD value uses its UTC day's price, as in features
  002 and 003, even when its local date differs. The summary time zone only decides periods.
- **Current moment**: the current period is decided once per run, from the run's clock, so all
  three summaries agree.
- **Width check**: "wide enough" means the terminal's width in columns is at least the width of
  the side-by-side layout for the figures being shown, which can grow with the size of the
  values. The width is read once per run.
- **Output stream**: the summaries go to standard output with the run's other lines, separated
  from the export line by a blank line. Errors still go to standard error (feature 001).
- **Golden files**: the summaries are report output under the constitution, so their layout
  is locked by golden-file tests created in this feature, for both layouts.
- **No new data**: the summaries use only the recorded transactions and prices; no schema
  change or new price lookups.
- **Out of scope**: the monthly summary CSV, configurable ranges (number of weeks, months, or
  years), other currencies, choosing which summaries to show, colors, and an option to hide
  the summaries.
