# Contract: the on-screen income summaries

The text printed after the export line by every successful run. This is report output under
the constitution: any change to it must be stated in a spec and update the golden files
(`tests/golden/summaries_*.txt`) in the same change.

## Placement

On standard output, after feature 003's `Exported …` line:

1. one blank line;
2. the three summaries, in one of the two layouts below, or the no-transactions message;
3. if any mark appears: one blank line, then the legend.

The tables are drawn by rich (research R7). Figures, labels and marks are ASCII. Borders use
rich's `box.ROUNDED` Unicode box-drawing characters. On a terminal, headers are bold and
titles use rich's default title style. Redirected output is plain text with no ANSI codes.

## Ranges

With *today* being the run clock's date in the summary time zone ([config.md](config.md)):

| Summary | Title | Periods, oldest first | Label |
|---------|-------|-----------------------|-------|
| Weekly | `Weekly Summary` | The 26 ISO weeks ending with today's week | `YYYY-Www`, ISO week-numbering year, week zero-padded (`2026-W07`) |
| Monthly | `Monthly Summary` | The 12 calendar months ending with today's month | `YYYY-MM` |
| Annual | `Annual Summary` | The 4 calendar years ending with today's year | `YYYY` |

A transaction counts in the period containing its local date: its recorded moment converted
to the summary time zone. Transactions outside a summary's periods count in none of its rows
and not in its total.

## One table

A rich `Table(title=<title>, box=box.ROUNDED, header_style="bold")`:

```text
                  <Title, centered>
╭──────────┬────────────────────┬────────────────╮
│ Period   │                XMR │            USD │
├──────────┼────────────────────┼────────────────┤
│ <period> │              <xmr> │   <usd> <marks>│   one row per period, oldest first
├──────────┼────────────────────┼────────────────┤
│ Total    │              <xmr> │   <usd> <marks>│
╰──────────┴────────────────────┴────────────────╯
```

- **Columns**:
  - `Period` is left-aligned; `XMR` and `USD` are right-aligned.
  - None of the columns wrap.
  - rich sizes each column to its widest cell, header included, with one space of padding
    on each side.
- **Total**: the `Total` row follows a section rule (`table.add_section()`).
- **XMR**: the exact sum of the period's amounts, priced or not. The whole part is grouped
  with `,` and followed by `.` and exactly 12 digits, ungrouped: `0.000000000000`,
  `1,234.500000000000`.
- **USD**:
  - the exact sum of the period's priced transactions' values (amount × its UTC day's price);
  - rounded once to the cent, half up;
  - written as `$`, the whole part grouped with `,`, then `.` and exactly 2 digits: `$0.00`,
    `$1,234,567.90`;
  - unpriced transactions add nothing.
- **Total figures**: XMR and USD summed exactly over the rows shown, then formatted the same
  way (the USD is rounded once).
- **Marks**: they are part of the USD cell, after the figure:
  - `*`: the figure includes at least one transaction valued at a provisional price;
  - `?`: the figure leaves out at least one transaction whose day has no price.

  When any row of a table has a mark, every USD cell in that table ends with a space and its
  marks, padded to the table's longest mark, so the figures stay aligned. A total carries
  every mark that any of its rows carries.
- **Cell text**: every cell is plain text, never parsed as markup or highlighted.

## Layouts

The CLI gives the renderer the terminal's width in columns when standard output is a
terminal, and no width otherwise. Table widths are rich's measured widths.

- **Side by side**: used when a width is given and it is at least *W* =
  weekly table width + 4 + max(monthly table width, annual table width). It is a rich grid
  with 4 columns of padding between its two cells:
  - the weekly table on the left;
  - the monthly table, a blank line, and the annual table on the right.
- **One after another**: used otherwise. It shows the weekly table, a blank line, the monthly
  table, a blank line, then the annual table.
- **Console width**: the text is rendered at a width of at least the chosen layout's width,
  so rich never shrinks a column or truncates a figure. When the legend is shown, the width
  is also at least its longest line, so rich never wraps it. On a terminal narrower than one
  table, the terminal wraps the lines instead.
- **Trailing spaces**: rich pads titles and the grid's cells with spaces, so lines may end
  in spaces. Golden comparisons strip trailing spaces from each line.

The periods, figures, marks, and legend are identical in both layouts (FR-015).

## Legend

Shown only if a mark appears anywhere in the three summaries. It lists only the marks that
appear, `*` first:

```text
* includes a provisional price, which may still change
? leaves out transactions that have no price yet
```

## No transactions

When no transactions are recorded at all, this single line replaces the summaries and the
legend:

```text
No transactions to summarize yet.
```

If transactions are recorded but all fall outside the ranges, the summaries are shown with
zeros instead of the message.

## Example

Today is 2026-10-27 in America/New_York. The recorded transactions are:

| Moment (UTC) | XMR | Day's price |
|--------------|-----|-------------|
| 2025-03-14T09:00:00Z | 1.5 | 150, final |
| 2026-05-05T12:00:00Z | 0.25 | 160.004, final |
| 2026-06-10T08:30:00Z | 1234.5 | 152.345, final |
| 2026-10-20T18:45:10Z | 0.731 | none |
| 2026-10-27T11:00:00Z | 2 | 163.40000000000001, provisional |

Side by side (needs 103 columns; trailing spaces not shown):

```text
                  Weekly Summary                                       Monthly Summary
╭──────────┬────────────────────┬────────────────╮    ╭─────────┬────────────────────┬────────────────╮
│ Period   │                XMR │            USD │    │ Period  │                XMR │            USD │
├──────────┼────────────────────┼────────────────┤    ├─────────┼────────────────────┼────────────────┤
│ 2026-W19 │     0.250000000000 │         $40.00 │    │ 2025-11 │     0.000000000000 │          $0.00 │
│ 2026-W20 │     0.000000000000 │          $0.00 │    │ 2025-12 │     0.000000000000 │          $0.00 │
│ 2026-W21 │     0.000000000000 │          $0.00 │    │ 2026-01 │     0.000000000000 │          $0.00 │
│ 2026-W22 │     0.000000000000 │          $0.00 │    │ 2026-02 │     0.000000000000 │          $0.00 │
│ 2026-W23 │     0.000000000000 │          $0.00 │    │ 2026-03 │     0.000000000000 │          $0.00 │
│ 2026-W24 │ 1,234.500000000000 │    $188,069.90 │    │ 2026-04 │     0.000000000000 │          $0.00 │
│ 2026-W25 │     0.000000000000 │          $0.00 │    │ 2026-05 │     0.250000000000 │         $40.00 │
│ 2026-W26 │     0.000000000000 │          $0.00 │    │ 2026-06 │ 1,234.500000000000 │    $188,069.90 │
│ 2026-W27 │     0.000000000000 │          $0.00 │    │ 2026-07 │     0.000000000000 │          $0.00 │
│ 2026-W28 │     0.000000000000 │          $0.00 │    │ 2026-08 │     0.000000000000 │          $0.00 │
│ 2026-W29 │     0.000000000000 │          $0.00 │    │ 2026-09 │     0.000000000000 │          $0.00 │
│ 2026-W30 │     0.000000000000 │          $0.00 │    │ 2026-10 │     2.731000000000 │     $326.80 *? │
│ 2026-W31 │     0.000000000000 │          $0.00 │    ├─────────┼────────────────────┼────────────────┤
│ 2026-W32 │     0.000000000000 │          $0.00 │    │ Total   │ 1,237.481000000000 │ $188,436.70 *? │
│ 2026-W33 │     0.000000000000 │          $0.00 │    ╰─────────┴────────────────────┴────────────────╯
│ 2026-W34 │     0.000000000000 │          $0.00 │
│ 2026-W35 │     0.000000000000 │          $0.00 │                     Annual Summary
│ 2026-W36 │     0.000000000000 │          $0.00 │    ╭────────┬────────────────────┬────────────────╮
│ 2026-W37 │     0.000000000000 │          $0.00 │    │ Period │                XMR │            USD │
│ 2026-W38 │     0.000000000000 │          $0.00 │    ├────────┼────────────────────┼────────────────┤
│ 2026-W39 │     0.000000000000 │          $0.00 │    │ 2023   │     0.000000000000 │          $0.00 │
│ 2026-W40 │     0.000000000000 │          $0.00 │    │ 2024   │     0.000000000000 │          $0.00 │
│ 2026-W41 │     0.000000000000 │          $0.00 │    │ 2025   │     1.500000000000 │        $225.00 │
│ 2026-W42 │     0.000000000000 │          $0.00 │    │ 2026   │ 1,237.481000000000 │ $188,436.70 *? │
│ 2026-W43 │     0.731000000000 │        $0.00 ? │    ├────────┼────────────────────┼────────────────┤
│ 2026-W44 │     2.000000000000 │      $326.80 * │    │ Total  │ 1,238.981000000000 │ $188,661.70 *? │
├──────────┼────────────────────┼────────────────┤    ╰────────┴────────────────────┴────────────────╯
│ Total    │ 1,237.481000000000 │ $188,436.70 *? │
╰──────────┴────────────────────┴────────────────╯

* includes a provisional price, which may still change
? leaves out transactions that have no price yet
```

One after another (needs 54 columns, for the legend's first line; trailing spaces not shown):

```text
                  Weekly Summary
╭──────────┬────────────────────┬────────────────╮
│ Period   │                XMR │            USD │
├──────────┼────────────────────┼────────────────┤
│ 2026-W19 │     0.250000000000 │         $40.00 │
│ 2026-W20 │     0.000000000000 │          $0.00 │
│ 2026-W21 │     0.000000000000 │          $0.00 │
│ 2026-W22 │     0.000000000000 │          $0.00 │
│ 2026-W23 │     0.000000000000 │          $0.00 │
│ 2026-W24 │ 1,234.500000000000 │    $188,069.90 │
│ 2026-W25 │     0.000000000000 │          $0.00 │
│ 2026-W26 │     0.000000000000 │          $0.00 │
│ 2026-W27 │     0.000000000000 │          $0.00 │
│ 2026-W28 │     0.000000000000 │          $0.00 │
│ 2026-W29 │     0.000000000000 │          $0.00 │
│ 2026-W30 │     0.000000000000 │          $0.00 │
│ 2026-W31 │     0.000000000000 │          $0.00 │
│ 2026-W32 │     0.000000000000 │          $0.00 │
│ 2026-W33 │     0.000000000000 │          $0.00 │
│ 2026-W34 │     0.000000000000 │          $0.00 │
│ 2026-W35 │     0.000000000000 │          $0.00 │
│ 2026-W36 │     0.000000000000 │          $0.00 │
│ 2026-W37 │     0.000000000000 │          $0.00 │
│ 2026-W38 │     0.000000000000 │          $0.00 │
│ 2026-W39 │     0.000000000000 │          $0.00 │
│ 2026-W40 │     0.000000000000 │          $0.00 │
│ 2026-W41 │     0.000000000000 │          $0.00 │
│ 2026-W42 │     0.000000000000 │          $0.00 │
│ 2026-W43 │     0.731000000000 │        $0.00 ? │
│ 2026-W44 │     2.000000000000 │      $326.80 * │
├──────────┼────────────────────┼────────────────┤
│ Total    │ 1,237.481000000000 │ $188,436.70 *? │
╰──────────┴────────────────────┴────────────────╯

                 Monthly Summary
╭─────────┬────────────────────┬────────────────╮
│ Period  │                XMR │            USD │
├─────────┼────────────────────┼────────────────┤
│ 2025-11 │     0.000000000000 │          $0.00 │
│ 2025-12 │     0.000000000000 │          $0.00 │
│ 2026-01 │     0.000000000000 │          $0.00 │
│ 2026-02 │     0.000000000000 │          $0.00 │
│ 2026-03 │     0.000000000000 │          $0.00 │
│ 2026-04 │     0.000000000000 │          $0.00 │
│ 2026-05 │     0.250000000000 │         $40.00 │
│ 2026-06 │ 1,234.500000000000 │    $188,069.90 │
│ 2026-07 │     0.000000000000 │          $0.00 │
│ 2026-08 │     0.000000000000 │          $0.00 │
│ 2026-09 │     0.000000000000 │          $0.00 │
│ 2026-10 │     2.731000000000 │     $326.80 *? │
├─────────┼────────────────────┼────────────────┤
│ Total   │ 1,237.481000000000 │ $188,436.70 *? │
╰─────────┴────────────────────┴────────────────╯

                 Annual Summary
╭────────┬────────────────────┬────────────────╮
│ Period │                XMR │            USD │
├────────┼────────────────────┼────────────────┤
│ 2023   │     0.000000000000 │          $0.00 │
│ 2024   │     0.000000000000 │          $0.00 │
│ 2025   │     1.500000000000 │        $225.00 │
│ 2026   │ 1,237.481000000000 │ $188,436.70 *? │
├────────┼────────────────────┼────────────────┤
│ Total  │ 1,238.981000000000 │ $188,661.70 *? │
╰────────┴────────────────────┴────────────────╯

* includes a provisional price, which may still change
? leaves out transactions that have no price yet
```

Notes on the example:

- 2026-W19's `$40.00` is 0.25 × 160.004 = 40.001, rounded once.
- 2026-W24's `$188,069.90` is 1234.5 × 152.345 = 188,069.9025.
- The 2026-10-20 transaction (no price) adds 0.731 XMR to 2026-W43 and October, but nothing to
  their USD. Those figures carry `?`.
- The 2026-10-27 provisional price makes 2026-W44 and October carry `*`.
- The 2025-03-14 transaction is in no weekly or monthly row, but it counts in 2025 and in the
  annual total.
- The weekly total, `$188,436.70`, is 40.001 + 188,069.9025 + 326.80000000000002, rounded
  once.
