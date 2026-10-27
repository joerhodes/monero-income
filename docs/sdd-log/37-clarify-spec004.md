# 37 - Clarify Spec 004 - Income Summaries

**Command:** /speckit-clarify
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-27

## Prompt
/speckit-clarify

## What Came Back
Question: Should the summary time zone also be settable with a command-line option, or only in the configuration file?

Why it matters: This decides whether the CLI gets a new option and how the precedence tests are written. Every other path-like setting (db_path, reports_path) has both, but settings like coin_id are config-only.

Recommended: Option A. The time zone rarely changes on a given machine, and a config-only setting keeps the usage line short. You can still add an option later without breaking anything.

┌────────┬────────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                    Description                                     │
├────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ A      │ Configuration file only                                                            │
├────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ B      │ Configuration file and a command-line option (option wins, as with --reports-path) │
├────────┼────────────────────────────────────────────────────────────────────────────────────┤
│ C      │ Command-line option only                                                           │
└────────┴────────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
B

## What Came Back
Recorded in the spec. I updated US4, FR-005, FR-006, the Summary time zone entity, and the Time zone setting assumption.

Question: Should XMR figures in the summaries use thousand separators like USD does (for example, 1,234.500000000000), or none (1234.500000000000)?

Why it matters: This sets how every XMR cell looks and how wide the column is, and the golden-file tests lock it in.

Recommended: Option A. Most incomes are well under 1,000 XMR, so a separator would rarely appear. Leaving it out matches the export, where XMR is written the same way.

┌────────┬────────────────────────────────────────────────────────────┐
│ Option │                        Description                         │
├────────┼────────────────────────────────────────────────────────────┤
│ A      │ No thousand separators for XMR (1234.500000000000)         │
├────────┼────────────────────────────────────────────────────────────┤
│ B      │ Thousand separators for XMR, like USD (1,234.500000000000) │
└────────┴────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
B

## What Came Back
Recorded. I updated FR-009, the Large values edge case, and the Number format assumption.

Question: If the run writes the export but then can't read the recorded data for the summaries, should it still print the sync, pricing, and export lines before the error?

Why it matters: In feature 003, a failed export hides all of a run's earlier lines. Here the export was already written, so hiding the "Exported …" line would leave you unsure whether the file is current. This changes the error-path tests.

Recommended: Option A. The export really was written, so say so, then report the error and exit with a failure status. Your record of what happened stays complete.

┌────────┬───────────────────────────────────────────────────────────────────┐
│ Option │                            Description                            │
├────────┼───────────────────────────────────────────────────────────────────┤
│ A      │ Print the sync, pricing, and export lines, then the error; exit 1 │
├────────┼───────────────────────────────────────────────────────────────────┤
│ B      │ Print only the error, as for other failures; exit 1               │
├────────┼───────────────────────────────────────────────────────────────────┤
│ C      │ Print all lines plus a warning instead of the summaries; exit 0   │
└────────┴───────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
A

## What Came Back
Clarification is done: I asked three questions and you answered all three

All four answers are recorded in specs/004-income-summaries/spec.md: these three, plus the dollar-sign clarification from earlier today.

┌─────┬─────────────────────────────────────────┬────────────────────────────────────────┬─────────────────────────────────────────────────────────┐
│  #  │                Question                 │              Your answer               │                Where it went in the spec                │
├─────┼─────────────────────────────────────────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│     │ Time zone: config file, option, or      │ Both; the option wins, then the file,  │ US4 (intro, Independent Test, new scenario 3), FR-005,  │
│ 1   │ both?                                   │ then the machine's time zone           │ FR-006, Summary time zone entity, Time zone setting     │
│     │                                         │                                        │ assumption                                              │
├─────┼─────────────────────────────────────────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│ 2   │ Thousand separators for XMR?            │ Yes, e.g. 1,234.500000000000           │ FR-009, Large values edge case, Number format           │
│     │                                         │                                        │ assumption                                              │
├─────┼─────────────────────────────────────────┼────────────────────────────────────────┼─────────────────────────────────────────────────────────┤
│     │ If the summaries can't be read after    │ Yes: the earlier lines, then the       │ FR-018, the edge case about reading data for the        │
│ 3   │ the export, still print the earlier     │ error, exit 1                          │ summaries                                               │
│     │ lines?                                  │                                        │                                                         │
└─────┴─────────────────────────────────────────┴────────────────────────────────────────┴─────────────────────────────────────────────────────────┘

Sections changed: Clarifications, User Story 4, Edge Cases, Functional Requirements, Key Entities, Assumptions. I also rewrapped the four lines my edits made too long.

Spec quality checklist: 16/16 → 16/16 passing. No item changed state.

Coverage

┌────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│            Category            │                                                     Status                                                      │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Functional scope and behavior  │ Clear                                                                                                           │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Domain and data model          │ Clear                                                                                                           │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Interaction and UX flow        │ Resolved (Q2, Q3)                                                                                               │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Non-functional (performance,   │ Clear                                                                                                           │
│ layout height)                 │                                                                                                                 │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Integration and configuration  │ Resolved (Q1)                                                                                                   │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Edge cases and failure         │ Resolved (Q3)                                                                                                   │
│ handling                       │                                                                                                                 │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Constraints and tradeoffs      │ Clear                                                                                                           │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Terminology                    │ Clear                                                                                                           │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Completion signals             │ Clear                                                                                                           │
├────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Placeholders                   │ Deferred: the setting's key and option name, the mark characters, the legend wording and the no-transactions    │
│                                │ message are left to planning on purpose. The golden files will lock them.                                       │
└────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

Nothing that matters is still open, so you can go straight to planning.
