# 27 - Clarify Spec 003

**Command:** /speckit-clarify
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-26

## Prompt
/speckit-clarify

## What Came Back
Question: Who should be able to read the export file each time a run replaces it? (FR-007)

Why it matters: The export lists every wallet transaction ID and amount in plain text. Replacing a file creates a new one, so permissions you set by hand on the old file would be lost on every run unless the spec says otherwise.

Recommended: Option A. The tool already warns when the config file is readable by other users, and the constitution treats wallet data as private. Owner-only is the safe default, and you can still copy the file to share it with an auditor.

┌────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                              Description                                              │
├────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ A      │ Owner only (read/write for you, nothing for others), every time it's written                          │
├────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ B      │ Your system's default for new files (usually readable by everyone on the machine)                     │
├────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ C      │ Keep the previous export's permissions when replacing it; use the system default for the first export │
├────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                                                          │
└────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
A

## What Came Back
I've recorded that and added FR-026, SC-009, a new acceptance scenario, and an edge case.

Question: If the run records transactions and prices but then can't write the export, should the run end with a failure status? (FR-008)

Why it matters: The exit status is what a scheduled job or script checks. Treating a missed export as a failure makes it visible. Treating it as a warning matches how feature 002 handles price-source problems: the data was saved, so the run "worked."

Recommended: Option A. The export is an audit record and a backup. If writing it fails silently on a scheduled run, the backup could go stale for weeks without anyone noticing. Unlike a price-source outage, a broken output path won't fix itself on the next run.

┌────────┬────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                            Description                                             │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ A      │ Failure: error message and failure status; recorded data is kept; the previous export stays intact │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ B      │ Warning only: the run still succeeds; the previous export stays intact                             │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                                                       │
└────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
A

## What Came Back
I've recorded that and tightened FR-008 to match.

Question: When transactions don't arrive in block order by time, what should "oldest first" sort the rows by? (FR-010)

Why it matters: Monero block timestamps are set by miners and don't always increase with block height. A later block can carry an earlier timestamp. The sort key decides the row order, and the golden files will lock that order in place.

Recommended: Option A. An auditor reads timestamp_utc and expects it to increase down the file, and each row's price day also comes from its timestamp. Block height breaks ties, so the order is the same on every run.

┌────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                                Description                                                │
├────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ A      │ By timestamp_utc, then height, then txid (timestamps always increase; heights may occasionally step back) │
├────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ B      │ By height, then timestamp_utc, then txid (chain order; timestamps may occasionally step back)             │
├────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                                                              │
└────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
A

## What Came Back
I've recorded that and moved the decision out of Assumptions; FR-010 already says it.

Question: When a usd_value falls exactly halfway between two cents, which way should it round? (FR-017)

Why it matters: An auditor who recomputes xmr × usd_price needs to get the same cents as the file, and the documentation has to state the rule. Exact halves are rare, but they happen: a 12-decimal amount times a price with few decimals can land on a half cent.

Recommended: Option A. Half up is the rule most people and spreadsheets apply by hand (Excel's ROUND, for example), so an auditor's check will match. Banker's rounding only matters when you sum many rounded values, and summaries are a later feature that can total the exact values instead.

┌────────┬──────────────────────────────────────────────────────────────┐
│ Option │                         Description                          │
├────────┼──────────────────────────────────────────────────────────────┤
│ A      │ Half up: 0.125 → 0.13, 0.135 → 0.14                          │
├────────┼──────────────────────────────────────────────────────────────┤
│ B      │ Half to even (banker's rounding): 0.125 → 0.12, 0.135 → 0.14 │
├────────┼──────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                 │
└────────┴──────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
A

## What Came Back
I've recorded that and moved it from Assumptions into the Clarifications section.

Question: Should a successful run print a line saying the export was written, for example Exported 1,234 transactions to /Users/you/reports/xmr_income.csv.? (FR-021)

Why it matters: Your description didn't mention one, and it would be the only change to the run's existing output. Without it, a run gives no sign that it wrote or replaced a file, or where.

Recommended: Option A. Every other step of the run (sync, pricing, import) already reports what it did. Showing the full path confirms where reports_path or --reports-path sent the file. The count shown follows the existing output style; the file itself never uses separators.

┌────────┬────────────────────────────────────────────────────────────────────────────────────────────┐
│ Option │                                        Description                                         │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ A      │ Yes: one line with the transaction count and the file's full path, after the pricing lines │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ B      │ Yes, but only the full path                                                                │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ C      │ No: the export is written silently; only failures are reported                             │
├────────┼────────────────────────────────────────────────────────────────────────────────────────────┤
│ Short  │ Provide a different short answer (<=5 words)                                               │
└────────┴────────────────────────────────────────────────────────────────────────────────────────────┘

You can reply with the option letter (e.g., "A"), accept the recommendation by saying "yes" or "recommended", or provide your own short answer.

## Answer
A

## What Came Back
I asked 5 questions, the session limit, and all 5 answers are now in specs/003-transaction-csv-export/spec.md.

┌─────┬─────────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  #  │              Question               │                                             Your answer                                              │
├─────┼─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1   │ Who can read the export?            │ Only you. Every time it's written, it's readable and writable by its owner only, even if you         │
│     │                                     │ loosened permissions on the previous file.                                                           │
├─────┼─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2   │ Does a failed export write fail the │ Yes. The run ends with a failure status; recorded data is kept and the previous export stays intact. │
│     │  run?                               │                                                                                                      │
├─────┼─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3   │ What does "oldest first" sort by?   │ timestamp_utc, then height, then txid.                                                               │
├─────┼─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4   │ Which way do half-cent values       │ Half up.                                                                                             │
│     │ round?                              │                                                                                                      │
├─────┼─────────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 5   │ Should a successful run print an    │ Yes: one line with the count and full path, e.g. Exported 1234 transactions to ….                    │
│     │ export line?                        │                                                                                                      │
└─────┴─────────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────┘

In my explanation for question 5, I said the count would use thousands separators to match the existing output. That was wrong. Feature 001 prints plain counts like Recorded N new transactions., so the spec says the count has no separators.

Sections changed: Clarifications (new), User Story 2 (one new acceptance scenario), Edge Cases, Functional Requirements (FR-008 and FR-021 tightened, FR-026 added), Success Criteria (SC-009 added), and Assumptions (two defaults removed now that they're decided).

Spec quality checklist: 16/16 passing before and after, with no items changing.

┌───────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────┐
│             Category              │                                          Status                                          │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Scope, out-of-scope, users        │ Clear                                                                                    │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Data, identity, ordering          │ Resolved (row order)                                                                     │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ User flow, error and empty cases  │ Resolved (export line, write failure)                                                    │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Reliability and recovery          │ Clear (all-or-nothing replace)                                                           │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Security and privacy              │ Resolved (owner-only access)                                                             │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Export format                     │ Resolved (rounding). Line endings are deferred to planning, then locked by golden files. │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Concurrent runs, failure handling │ Clear                                                                                    │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Terminology, testability          │ Clear                                                                                    │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Performance, scale                │ Clear (low impact)                                                                       │
├───────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────┤
│ Leftover placeholders             │ Clear                                                                                    │
└───────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────┘

Nothing high-impact is left open. Next step is /speckit-plan.
