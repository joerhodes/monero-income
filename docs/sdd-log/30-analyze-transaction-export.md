# 30 - Analyze tasks for transaction CSV export

**Command:** /speckit-analyze
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-26

## Prompt
/speckit-analyze

## What Came Back
Specification Analysis Report

I found no critical issues; the most serious is one HIGH (I1). Every requirement and success criterion has at least one task.

ID: I1
Category: Inconsistency
Severity: HIGH
Location(s): tasks.md T004 vs T005; spec FR-022
Summary: T004's code, _pick(...) or DEFAULT_REPORTS_PATH, turns an empty "" into the default before the blank check runs. So "" never errors, which
breaks FR-022 and T005's "" test case. Only whitespace like " " would raise. The db_path code that T004 says to mirror has the same gap, and no
existing test covers it.
Recommendation: In T004, check for a blank value from _pick before applying the default. Drop "Mirror the db_path code … exactly". Leave db_path alone;
it's outside this feature.
────────────────────────────────────────
ID: U1
Category: Underspecification
Severity: MEDIUM
Location(s): research R3; tasks T023; spec US3 ("an auditor's shared folder")
Summary: The lock on the reports folder (flock) can fail with ENOLCK/ENOTSUP on some network filesystems. T023 turns every such failure into a write
error, so exporting to a shared folder could fail on every run.
Recommendation: Decide in R3 and T023: either continue without the lock, skipping stale-file cleanup, when locking isn't supported; or keep failing and
document it in docs/export-csv.md. Either way, add a T020 case for it.
────────────────────────────────────────
ID: I2
Category: Inconsistency
Severity: MEDIUM
Location(s): README.md Status table (lines 27–28); tasks T029
Summary: The README roadmap says 003 is "[reports] weekly and monthly income tables" and puts CSV output in 004. T029 tells the implementer not to touch
the Status section, so the roadmap will contradict this feature.
Recommendation: Your call, since the README is your writing. Either allow T029 to update the Status rows, or edit them yourself.
────────────────────────────────────────
ID: U2
Category: Underspecification
Severity: LOW
Location(s): tasks T032; spec FR-019
Summary: Decimal(usd_price) == price compares numeric value, so "152.30" and "152.3" count as equal. That doesn't prove the text was written exactly.
Recommendation: Also assert usd_price == format(price, "f").
────────────────────────────────────────
ID: A1
Category: Ambiguity
Severity: LOW
Location(s): spec FR-018
Summary: "No value … MUST be written in …" is a double negative.
Recommendation: Reword: "Values MUST NOT be written in scientific notation or with thousands separators."
────────────────────────────────────────
ID: T1
Category: Terminology
Severity: LOW
Location(s): spec ("output directory") vs plan, contracts, tasks ("reports directory")
Summary: Two names for the same folder.
Recommendation: Pick one; "reports directory" matches the reports_path key.
────────────────────────────────────────
ID: U3
Category: Underspecification
Severity: LOW
Location(s): spec Assumptions ("File format … decided during planning")
Summary: Planning has decided this (research R5: LF, UTF-8, unquoted), but the spec still says it's open.
Recommendation: Update the assumption to point to contracts/export-csv.md.
────────────────────────────────────────
ID: A2
Category: Ambiguity
Severity: LOW
Location(s): tasks T017
Summary: "still inside the except (StorageError, WalletError) block" reads as if the write goes inside the error handler.
Recommendation: Reword: "still inside the outer try whose except (StorageError, WalletError) maps errors through _run_error".

Coverage Summary

┌────────────────┬───────────┬────────────────────────┬────────────────────────┐
│  Requirement   │ Has task? │        Task IDs        │         Notes          │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-001         │ ✅        │ T010, T017             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-002         │ ✅        │ T010, T017             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-003         │ ✅        │ T016                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-004         │ ✅        │ T004, T005, T025, T027 │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-005         │ ✅        │ T009, T015, T025       │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-006         │ ✅        │ T009                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-007         │ ✅        │ T020, T023             │ Shared-folder gap (U1) │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-008         │ ✅        │ T020–T024              │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-009         │ ✅        │ T011, T013             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-010         │ ✅        │ T007, T013             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-011–FR-017  │ ✅        │ T007, T011, T013       │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-018         │ ✅        │ T007, T032             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-019         │ ✅        │ T032                   │ U2                     │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-020         │ ✅        │ T010                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-021         │ ✅        │ T012, T018             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-022         │ ⚠️        │ T004, T005, T025       │ Conflict (I1)          │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-023         │ ✅        │ T028, T030             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-024         │ ✅        │ T008, T010, T014       │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-025         │ ✅        │ T031                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ FR-026         │ ✅        │ T015, T020             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-001         │ ✅        │ T010                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-002, SC-003 │ ✅        │ T032                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-004         │ ✅        │ T007, T032             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-005         │ ✅        │ T020, T021             │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-006         │ ✅        │ T010                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-007         │ ✅        │ T028, T030, T034       │ Partly a manual check  │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-008         │ ✅        │ T010                   │                        │
├────────────────┼───────────┼────────────────────────┼────────────────────────┤
│ SC-009         │ ✅        │ T020                   │                        │
└────────────────┴───────────┴────────────────────────┴────────────────────────┘

Constitution alignment: no conflicts. The new modules respect the layer rules (I) and keep the CLI thin (II). No float is used (III), and I/O stays separate from transformation (IV). Tests touch no network and write only under tmp_path (V). There's no schema change and nothing writes to the database (VI). The five checks stay in place (VII), and the golden files meet the workflow rule for report output.

Tasks with no requirement: T001 and T033 (setup and running the checks), as expected.

Metrics

┌──────────────────────┬─────────────────────────────────────────┐
│                      │                                         │
├──────────────────────┼─────────────────────────────────────────┤
│ Total requirements   │ 35 (26 FR, 9 SC)                        │
├──────────────────────┼─────────────────────────────────────────┤
│ Total tasks          │ 34                                      │
├──────────────────────┼─────────────────────────────────────────┤
│ Coverage             │ 100% (FR-022 has a task but a conflict) │
├──────────────────────┼─────────────────────────────────────────┤
│ Ambiguity findings   │ 2                                       │
├──────────────────────┼─────────────────────────────────────────┤
│ Duplication findings │ 0                                       │
├──────────────────────┼─────────────────────────────────────────┤
│ Critical issues      │ 0                                       │
└──────────────────────┴─────────────────────────────────────────┘

Next Actions

- Fix I1 before /speckit-implement. It's a one-line change to T004, and without it T005 fails or the implementer has to guess which is right.
- U1 and I2 need your decision:
  - U1: whether exporting to a network folder that can't be locked should work without the lock.
  - I2: whether T029 may update the README roadmap.
- The LOW items can be fixed in the same edit, or left.

Would you like me to suggest concrete remediation edits for the top 3 issues?

## Response
I1 - Accept recommendation.
U1 - Fail and report lock failures, document lock failures for export.
     Also update the spec: exports to a folder whose filesystem does not
     support file locking (some network shares) fail with a clear message;
     to share the export, write it locally and copy it.  Adjust the US3
     "shared folder" wording to match, and add the T020 test case.
I2 - README updated to show 003 is transaction CSV export.
U2 - Accept recommendation.
A1 - Accept recommendation.
T1 - Accept recommendation, use "reports directory".
U3 - Accept recommendation.
A2 - Accept recommendation.

## What Came Back
I've applied all eight decisions across the spec, plan, research, data model, contracts and tasks. Nothing is committed yet.

- I1 (empty reports_path): T004 now rejects an empty value before the default applies, so "" from the config file or the option is an error rather than silently becoming ~/reports. T004 also says to leave db_path's existing code alone. I added the empty cases to acceptance scenario US3-6, the config contract, and T025.
- U1 (filesystems without file locking): the export fails with a clear message, as you chose.
  - Spec: new requirement FR-027, a new edge case, and acceptance scenario US3-7. The US3 "Why this priority" no longer mentions an auditor's shared folder; it says to write locally and copy to a network share.
  - Research, data model and CLI contract: a new error type, ExportLockUnsupportedError, a subclass of the existing ExportWriteError. It's raised for the three "locking not supported" error codes. The contract fixes its message: the filesystem doesn't support file locking (some network shares don't); write the export to a local directory and copy it.
  - Tasks:
    - T002 defines the new error.
    - T023 raises it before any temporary file is created.
    - T020 tests each of the three error codes, plus one other error code that must stay a plain write error.
    - T025 covers it end to end through run().
    - T028 and T029 document the limitation in docs/export-csv.md and the README.
- I2 (README roadmap): you'd already updated the Status table, so I only changed T029 to note that.
- U2: T032 now also checks that usd_price is written exactly as stored, character for character, not just numerically equal.
- A1: FR-018 now reads "Values MUST NOT be written in scientific notation or with thousands separators."
- T1: "reports directory" is now used everywhere. The one exception is your original feature description, quoted word for word in the spec's Input line, which I left as written.
- U3: the line-endings assumption now points to the format contract. I fixed the same out-of-date note in the spec quality checklist.
- A2: T017's wording now says the write goes inside the outer try, not inside the error handler.

There are still 34 tasks; the new work went into existing tasks rather than new ones.

Next is /speckit-implement. You could rerun /speckit-analyze first if you want these edits rechecked.
