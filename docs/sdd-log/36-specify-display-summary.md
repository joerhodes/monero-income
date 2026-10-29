# 36 - Specify behavior for displaying income summaries

**Command:** /speckit-specify
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-27

## Prompt
/speckit-specify monero-income records a Monero wallet's incoming
transactions (feature 001), values them in USD (feature 002), and exports
them to a CSV file (feature 003). This feature displays income summaries
on screen, giving the user an at-a-glance view of recent income by week,
month, and year. The monthly summary CSV and Configurable ranges are out
of scope.

Behaviors:
- Every run that completes sync, pricing, and export displays three
  summaries: the last 26 weeks, the last 12 months, and the last 4
  years, each including the current, partial period.
- Periods are calendar periods in the local time zone (the machine's by
  default, or the configured one): ISO weeks (labeled YYYY-Www), months
  (YYYY-MM), and years (YYYY). Periods with no transactions are shown with
  zero values. Rows are ordered oldest first.
- Each summary has columns Period, XMR (12 decimal places), and USD
  (rounded to the cent, half-cents away from zero, with thousand separators),
  and a final total row covering only the periods shown.
- Totals are summed at full precision and rounded once. A transaction
  without a price adds its XMR but nothing to USD.
- A USD value that includes a provisional price, or that excludes an
  unpriced transaction, is marked, with a short legend explaining the
  marks.
- Layout: when the terminal is wide enough, the weekly summary appears
  on the left, with the monthly and annual summaries stacked to its right:
  +---------+-----------------+
  | Weekly  | Monthly Summary |
  | Summary | Annual Summary  |
  +---------+-----------------+
  When the terminal is too narrow, or the output is not a terminal, the
  summaries are printed one after another: weekly, monthly, annual.
- With no recorded transactions, a single message replaces the summaries.

## What Came Back
Spec for feature 004 is written

- Branch: 004-income-summaries, created from main after 003 was merged.
- Feature directory: specs/004-income-summaries/, and .specify/feature.json now points to it.
- Spec file: specs/004-income-summaries/spec.md
- Checklist: checklists/requirements.md passes all 16 items, and the spec has no [NEEDS CLARIFICATION] markers.

The spec has four user stories:
- US1 (P1): the three summaries, printed one after another.
- US2 (P2): marks on USD figures that include a provisional price or leave out an unpriced transaction, with a legend.
- US3 (P2): the side-by-side layout on a wide terminal.
- US4 (P3): a configured time zone.

There are 21 functional requirements and 7 success criteria.

Decisions I made that your description didn't settle (all listed under Assumptions):
- Time zone setting: there isn't one yet, so this feature adds a config-file-only setting that takes an IANA time zone name. It has no command-line option, and planning names the key.
- Price day: a transaction is grouped by its local date but still valued at its UTC day's price. The spec has a worked example of a transaction near midnight.
- Marks on totals: a total's USD carries a mark when any period in that summary does. The legend lists only the marks that appear, and is left out when none do.
- Number format: XMR has no thousand separators. USD always uses , and ., whatever the machine's locale.
- Left to planning: the exact mark characters and legend text, the no-transactions message, and the layout widths, all locked by golden files.
- Output position: the summaries come after the export line, separated by a blank line. If the database can't be read for the summaries, the run fails, but the export it already wrote stays.

I checked the calendar examples with Python. One of my first examples was wrong: 2026-11-01 is a Sunday, so it's in W44 in both UTC and New York. I replaced it with a Sunday-night case that does change weeks (W43 local vs W44 UTC).

Suggested next step: /speckit-clarify. Two open questions are worth settling there:
- Should the time zone also have a command-line option?
- Should XMR figures use thousand separators like USD?

Nothing is committed. The untracked docs/sdd-log/36-…md is yours, and I didn't touch it.

## Edit Prompt
Update the spec: on-screen USD values are shown with a dollar sign,
e.g. $1,234,567.90. Update every example and acceptance scenario that
shows a USD value, and add a Clarifications entry. Change nothing else.

## What Came Back
I updated the spec. Every on-screen USD value in the examples and acceptance scenarios now has a dollar sign:

- US1 scenario 4: $0.00
- US1 scenario 5: $265.00
- US1 scenario 6: $1,234,567.90
- US2 scenario 4: $0.00
- Edge cases: the half-cent rounding result is now $0.13, and the large-values example is now $1,234,567.90

I added a new ## Clarifications section (Session 2026-10-27) after the Input line, in the same format as spec 003.

I left some USD amounts alone because they aren't shown on screen: the recorded prices (150.00 USD, 160.004 USD) and the exact amounts before rounding (0.125, 1234567.895, 225 + 40.001 = 265.001).

Since you asked me to change nothing else, the requirements still don't mention the dollar sign:
- FR-010 says USD is shown with 2 decimal places and thousand separators, but not with a $.
- The Number format assumption describes the , and . separators only.

So right now only the examples and the Clarifications entry call for the $. Should I add it to FR-010 and the Number format assumption?


## Response
Yes, update FR-101 and the Number format assumption.

## What Came Back
FR-010 and the Number format assumption now both require the dollar sign. I took your "FR-101" to mean FR-010, since the spec has no FR-101.

- FR-010: USD is now "shown with a leading dollar sign, exactly 2 decimal places, and thousand separators (for example, $1,234,567.90)".
- Number format assumption: it now reads "USD starts with $ and uses , as the thousand separator and . as the decimal point, whatever the machine's locale."

The edits made those paragraphs longer, so I rewrapped them to the spec's line width. Nothing else in the spec changed.
