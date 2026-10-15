# 10 - Analyze for Spec 001

**Command:** /speckit-analyze
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-15

## Prompt
/speckit-analyze

## What Came Back
Specification Analysis Report

I checked spec.md, plan.md, tasks.md, the plan's supporting design files and the constitution (v1.2.0) against each other. I didn't change any files.

ID: C1
Category: Constitution
Severity: CRITICAL
Location(s): contracts/run-api.md (wallet_factory default); tasks.md Notes, T016, T028
Summary: The contract's default HttpWalletRpc.from_settings would make primitives import
orchestration's Settings. That breaks Principle I (dependencies point inward only). tasks.md
works around it, but the contract still specifies the violation.
Recommendation: Change the default in run-api.md to an orchestration-level
make_wallet(settings), matching T028. Then drop the workaround note from tasks.md.
────────────────────────────────────────
ID: I1
Category: Inconsistency
Severity: HIGH
Location(s): T028 (run() closes conn in finally); T032, T034, T038; contracts/run-api.md (test
seams)
Summary: run() closes the connection it opens, but closing an in-memory SQLite database deletes
it. Every test that runs run() twice on one in-memory database (T032 second run, T038 "next
run equals…") loses its data. T038's check of conn.in_transaction after run() would fail on a
closed connection.
Recommendation: Use tmp_path database files for multi-run tests (allowed by Principle V), or
make whoever creates the connection responsible for closing it. State the choice in run-api.md
 and T028.
────────────────────────────────────────
ID: U1
Category: Underspecification
Severity: HIGH
Location(s): T032, T034, T038, T039 (only T023 sets config_path); constitution V ("Tests MUST
NOT touch real user data")
Summary: run() defaults to the real ~/.config/monero-income/config.toml. Any integration test
that forgets config_path= reads the developer's real config, which may contain the wallet
password.
Recommendation: Add a tests/conftest.py task with an autouse fixture that redirects
HOME/config_path to tmp_path, or require config_path in every run() test.
────────────────────────────────────────
ID: G1
Category: Coverage gap
Severity: HIGH
Location(s): spec FR-002, SC-001 ("100% of … incoming transactions"); research R6;
contracts/wallet-rpc.md
Summary: get_transfers without all_accounts returns only account 0. Payouts to other accounts
are silently never recorded, contradicting FR-002 and SC-001. I raised this earlier and it
hasn't been decided.
Recommendation: Either add a spec assumption ("payouts go to account 0") or add all_accounts:
true to the request (contract, T015, T016).
────────────────────────────────────────
ID: I2
Category: Inconsistency
Severity: MEDIUM
Location(s): data-model.md (PK conflict → storage error); T012; T042; contracts/cli.md
"Database
unreadable"
Summary: StorageError from an insert (a primary-key conflict from a concurrent run, or an
amount
overflow) is shown as cannot read database … The file was not changed. That's false once
earlier windows were committed, and it isn't a read failure.
Recommendation: Add a "cannot write to database" category to cli.md, and split the insert-time
error from the open-time error in T012 and T042.
────────────────────────────────────────
ID: I3
Category: Inconsistency
Severity: MEDIUM
Location(s): T009, T012 (StorageError/SchemaTooNewError); T014 [P], T016 (WalletResponseError)
Summary: Circular or out-of-order definitions. T009 needs StorageError from T012's module (with
an "or define here and re-export" fallback). T014 is marked parallel but imports from T016.
Recommendation: Create primitives/errors.py (add it to the plan's structure) in an early task
holding all primitive errors. Remove [P] from T014 or make it depend on that task.
────────────────────────────────────────
ID: G2
Category: Coverage gap
Severity: MEDIUM
Location(s): spec US1 scenario 2, US1 Independent Test; quickstart US1-2; T021, T023
Summary: The "incoming + outgoing → only incoming" scenario has no run-level test. FR-003 is
enforced only by T015's "out": false check, and the fake can't hold outgoing entries.
Recommendation: Have T023 state that FR-003 is covered by T015's request-parameter assertion,
and update quickstart US1-2 to match. Or teach the fake to ignore outgoing entries.
────────────────────────────────────────
ID: B1
Category: Ambiguity
Severity: LOW
Location(s): T044
Summary: "Exempt the RPC method name only if it appears in orchestration; it should live in
primitives" is self-contradictory. Since the scan only covers cli and orchestration, no
exemption should be needed.
Recommendation: Replace with: "no exemptions; get_transfers lives only in primitives, which
isn't scanned."
────────────────────────────────────────
ID: I4
Category: Inconsistency
Severity: LOW
Location(s): data-model.md resolve_settings(cli, file, defaults); T020
resolve_settings(options,
 raw, config_path)
Summary: The signature differs between the two.
Recommendation: Align data-model.md with T020.
────────────────────────────────────────
ID: U2
Category: Underspecification
Severity: LOW
Location(s): data-model.md (CHECK (height > 0)); T013, T014 (parse rejects only negative
values)
Summary: A wallet entry at height 0 passes parsing but fails the database CHECK, and would show
up with the misleading database-read message.
Recommendation: Have T014 also reject height == 0.
────────────────────────────────────────
ID: U3
Category: Underspecification
Severity: LOW
Location(s): data-model.md ("can only come from a concurrent run"); spec Edge Cases
Summary: Two simultaneous runs aren't addressed in the spec.
Recommendation: Add an edge case: a second concurrent run may fail with a storage error, and no
data is lost.
────────────────────────────────────────
ID: I5
Category: Inconsistency
Severity: LOW
Location(s): contracts/cli.md "Interrupted"; T040, T043
Severity: LOW
Location(s): data-model.md (CHECK (height > 0)); T013, T014 (parse rejects only negative values)
Summary: A wallet entry at height 0 passes parsing but fails the database CHECK, and would show
up with the misleading database-read message.
Recommendation: Have T014 also reject height == 0.
────────────────────────────────────────
ID: D1
Category: Duplication
Severity: LOW
Location(s): spec FR-009 and FR-010 vs SC-003; FR-013 and FR-014 vs SC-004
Summary: Requirements are restated as success criteria.
Recommendation: No action; a requirement and its measure are acceptable.

Coverage Summary

┌───────────────────────────────────┬─────────┬────────────────┬──────────────────────────┐
│          Requirement Key          │  Has    │    Task IDs    │          Notes           │
│                                   │  Task?  │                │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-001 sync-is-first-step         │ ✅      │ T025, T030     │ --help: no subcommands   │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-002 record-all-incoming        │ ✅      │ T023, T027     │ See G1 (account 0 only)  │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-003 no-outgoing                │ ✅      │ T015, T016     │ Request parameter only,  │
│                                   │         │                │ see G2                   │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-004 one-confirmation           │ ✅      │ T015, T016     │ pending/pool=false       │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-005 record-fields              │ ✅      │ T009, T023     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-006 exact-amount               │ ✅      │ T023, T013     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-007 tz-independent-time        │ ✅      │ T008, T023     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-008 txid-identity-and-sum      │ ✅      │ T022, T023,    │                          │
│                                   │         │ T032           │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-009 never-modify               │ ✅      │ T010, T012,    │                          │
│                                   │         │ T032           │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-010 no-change-when-nothing-new │ ✅      │ T032           │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-011 no-new-message             │ ✅      │ T033, T037     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-012 count-message              │ ✅      │ T025, T030     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-013 keep-on-interrupt          │ ✅      │ T038, T041     │ See I1                   │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-014 resume-completes           │ ✅      │ T038           │ See I1                   │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-015 errors-no-traceback        │ ✅      │ T039, T040,    │                          │
│                                   │         │ T042, T043     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-016                            │ ✅      │ T011, T012,    │                          │
│ persist-create-never-recreate     │         │ T024           │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-017 wallet-url                 │ ✅      │ T019, T020,    │                          │
│                                   │         │ T025           │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-018 password-handling          │ ✅      │ T015, T019,    │                          │
│                                   │         │ T025, T039     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ FR-019 say-transactions           │ ✅      │ T039, T044     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ SC-001 all-incoming-recorded      │ ✅      │ T023, T015     │ See G1                   │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ SC-002 exact-12dp                 │ ✅      │ T023           │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ SC-003 idempotent                 │ ✅      │ T032           │ See I1                   │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ SC-004 interruption-equivalence   │ ✅      │ T038           │ See I1                   │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ SC-005 failed-runs-clean          │ ✅      │ T039, T040     │                          │
├───────────────────────────────────┼─────────┼────────────────┼──────────────────────────┤
│ SC-006 under-5s                   │ ✅      │ T034           │ See I1, U1               │
└───────────────────────────────────┴─────────┴────────────────┴──────────────────────────┘

Constitution Alignment Issues:
- C1 (Principle I): the plan's run-api contract makes primitives depend on orchestration. tasks.md avoids it, but the plan document still has it.
- U1 (Principle V) is a risk rather than a violation: nothing yet stops a test from reading the real config file.

Unmapped Tasks: T045 (README usage section) maps to no requirement; it's acceptable polish. Setup tasks T001–T005 serve constitution VII and Constraints.

Metrics
- Total requirements: 25 (19 FR + 6 SC)
- Total tasks: 47
- Coverage: 100% (25/25 have at least one task)
- Ambiguity count: 1
- Duplication count: 1
- Critical issues: 1

Next Actions

- Before /speckit-implement: resolve C1. It's a one-line edit to contracts/run-api.md.
- Should also be fixed first: the three HIGH items.
  - I1 and U1 would make several US2/US3 tests fail, or read real user data, as written. Fix them by editing tasks.md T028, T032, T034 and T038, adding a tests/conftest.py task, and editing run-api.md.
  - G1 needs your decision: "account 0 only" as a spec assumption, or all_accounts: true. Record it in spec.md (Assumptions), or in the request parameters in contracts/wallet-rpc.md plus tasks T015 and T016.
- MEDIUM items:
  - I2: add a write-error category in cli.md and T042.
  - I3: add primitives/errors.py.
  - G2: clarify how FR-003 is covered.
- LOW items can be fixed during implementation.

Would you like me to suggest concrete remediation edits for the top 7 issues (C1, I1, U1, G1, I2, I3, G2)?

## Follow up Prompt 1
Spec changes to specs/001-sync-incoming-transactions/spec.md:
1. G1: add an assumption that the tool reads account 0 of the wallet
   only, where mining payouts arrive; other accounts are out of scope.
2. U3: add an edge case: a second run started while one is in progress
   may fail with a storage error, and no recorded data is lost.
Add a Clarifications entry for both. Change nothing else.

## What Came Back
I made both changes to spec.md, and nothing else in it changed.

1. G1, account 0 only: I added an assumption, right after "The tool works with one wallet": "The tool reads account 0 of the wallet only, where mining payouts arrive. Other accounts are out of scope." This brings FR-002 and SC-001 in line with the wallet request, which doesn't set all_accounts.
2. U3, a second run started during another: I added an edge case after "Very large history": "the second run may fail with a storage error; no recorded data is lost."
3. Clarifications: I added a Q&A entry for each decision to the existing Session 2026-10-15 section.

Still open from the analysis:
- C1 (CRITICAL): the run-api contract's default wallet factory breaks the layering rule (Principle I).
- I1: run() closes the connection, which deletes an in-memory test database between runs.
- U1: tests could read your real config file.
- I2: errors writing to the database are reported with the "cannot read database" message.
- I3: error classes are defined out of order between tasks.
- G2: "only incoming recorded" has no run-level test.

Two notes on the new text:
- The concurrent-run case relies on the database write error that I2 is about. Under the current mapping, a second run would see cannot read database … The file was not changed, which is misleading. Fixing I2 would give it an accurate message.
- research.md R6 and contracts/wallet-rpc.md still describe the account-0 limit as an open finding. They can now point to the new assumption.

## Follow up Prompt 2
Apply the analyze remediations to the plan artifacts and tasks.md:
C1 as recommended; I1 using tmp_path database files for multi-run
tests; U1 with an autouse tests/conftest.py fixture redirecting HOME and
config_path to tmp_path; I2, I3, and G2 as recommended; and the LOW
items B1, I4, U2, and I5 as recommended. Reflect the G1 decision (account
0 only) in contracts/wallet-rpc.md and tasks T015/T016. Change nothing
unrelated.

## What Came Back
I applied all the requested remediations. tasks.md now has 49 tasks (two new ones), and every 
task ID and cross-reference is renumbered and still lines up.
                                                                                              
Item: C1
Change: contracts/run-api.md now defaults to make_wallet, which lives in orchestration. The
workaround note at the end of tasks.md is removed. T018 says the wallet client has no
settings-based constructor. That also fixes a stale "factory lives in T022" reference; it's
T030.
────────────────────────────────────────
Item: I1
Change: Tests that call run() more than once or read the database afterwards use tmp_path
files:
T025 (first sync), T034 (re-sync), T036 (performance), T040 (interruption). T040's Ctrl-C
check now reopens the file instead of inspecting a closed connection. I added the rule to the
task rules, run-api.md, quickstart.md and the plan's testing notes.
────────────────────────────────────────
Item: U1
Change: New T005: tests/conftest.py autouse fixture sets HOME to tmp_path. To make that work,
the default config path and db_path now expand ~ when run() is called, not at import:
config_path: Path | None = None in run-api.md, default_config_path() in T022 and T030.
────────────────────────────────────────
Item: I2
Change: StorageReadError and StorageWriteError are now separate. cli.md has a new "cannot write
to database … Transactions recorded before this error were kept." category, and data-model.md
calls a primary-key conflict a write error. T012, T014 and T044 are updated, and T041 adds an
overflow case to exercise the write error.
────────────────────────────────────────
Item: I3
Change: New T007: primitives/errors.py holds every primitive error, and the plan's source tree
lists it. The "define here or re-export" fallback is gone, and the dependency notes say T007
comes first.
────────────────────────────────────────
Item: G2
Change: T017 and T025 now say FR-003 (and the "only incoming recorded" scenario) is tested by
the "out": false assertion. The quickstart.md row for that scenario says the same.
────────────────────────────────────────
Item: G1
Change: contracts/wallet-rpc.md says no account parameters are sent, so only account 0 is
returned, as intended by the spec's Assumptions. T017 asserts that no account_index or
all_accounts key is sent, and T018 notes it.
────────────────────────────────────────
Item: B1
Change: T046 (the "transfer" wording test) now says "No exemptions: get_transfers lives only in
primitives, which isn't scanned."
────────────────────────────────────────
Item: I4
Change: data-model.md now uses the signature resolve_settings(options, raw, config_path) →
(Settings, warnings).
────────────────────────────────────────
Item: U2
Change: Parsing rejects a height of 0, in data-model.md, T015 and T016.
────────────────────────────────────────
Item: I5
Change: The Ctrl-C message is now "interrupted; anything already recorded was kept", in cli.md,
T042 and T045.

research.md R6 still calls the account-0 limit a finding rather than pointing to the spec's assumption. I left it because you asked me not to change anything unrelated.

Next step: run /speckit-analyze again to confirm the findings are cleared.


## Analysis Pass 2 Prompt
/speckit-analyze

## What Came Back
Specification Analysis Report (second pass)

All 13 findings from the first pass are fixed, and no constitution conflicts remain. This pass 
found three new MEDIUM issues and three LOW ones. I didn't change any files.                   
                                                                                               
ID: I6                                                                                         
Category: Inconsistency                                                                        
Severity: MEDIUM                                                                               
Location(s): tasks.md, Phase 4 "Independent Test"                                              
Summary: The US2 independent test still says "Run run() twice against the same fake and        
in-memory database". That contradicts the new task rule: run() closes its connection, which    
discards an in-memory database. The I1 edit missed this text.                                  
Recommendation: Change it to "…against the same fake and a tmp_path database file", matching   
T034.                                                                                          
────────────────────────────────────────                                                       
ID: U4                                                                                         
Category: Underspecification                                                                   
Severity: MEDIUM                                                                               
Location(s): tasks.md T040 "Partial window (FR-013)"                                           
Summary: The test asks for "a duplicate-txid failure in the middle of a window's insert", but  
nothing in the design can produce one. Duplicates within a window are merged by                
combine_by_txid, and already-recorded ids are dropped by select_new. Without a defined         
trigger, the test may not get written.                                                         
Recommendation: Use the overflow trigger from T041: a window holding one normal entry and one  
at                                                                                             
9,223,372,036,854,775,808 piconero. Assert that neither row is stored and that earlier windows 
 stay.                                                                                         
────────────────────────────────────────                                                       
ID: G3                                                                                         
Category: Coverage gap                                                                         
Severity: MEDIUM                                                                               
Location(s): spec Edge Cases ("Second run started while one is in progress"); tasks.md         
Summary: The new edge case (the second run may fail with a storage error, and no recorded data 
is lost) has no test. SQLite waits about 5 seconds for a lock before failing, which an         
implementer could easily miss.                                                                 
Recommendation: Add a US3 test in test_interruption.py. One connection holds a write           
transaction                                                                                    
on a tmp_path database while run() runs against the same file. Expect RunError containing      
cannot write to database (or cannot read database if the lock hits at open), with existing     
rows intact. Use a short SQLite lock timeout to keep the test fast.                            
────────────────────────────────────────                                                       
ID: L1                                                                                         
Category: Inconsistency                                                                        
Severity: LOW                                                                                  
Location(s): tasks.md T005; Dependencies ("T005 after T003")                                   
Summary: T005 (conftest) is marked [P] but depends on T003 creating tests/.
Recommendation: Drop the [P], or have T005 create tests/ itself.
────────────────────────────────────────
ID: L2
Category: Inconsistency
Severity: LOW
Location(s): research.md R6 (account-0 bullet)
Summary: It still frames the account-0 limit as a finding outside the decided request, though
the spec now makes it an assumption.
Recommendation: Add "intended; see spec Assumptions" when research.md is next edited.
────────────────────────────────────────
ID: L3
Category: Underspecification
Severity: LOW
Location(s): spec FR-012; contracts/cli.md (wallet error categories)
Summary: When a wallet error stops a run after some windows were committed, the message doesn't
say how many transactions were kept. Only write errors and Ctrl-C mention anything being kept.
 FR-012 arguably covers only successful runs.
Recommendation: Optional: say "N new transactions were recorded before the error" on any
failure                                                                                       
after commits, or state in the spec that FR-012 applies to successful runs only.

Coverage Summary

┌───────────────────────────────────┬─────────┬─────────────────┬─────────────────────────┐
│          Requirement Key          │  Has    │    Task IDs     │          Notes          │
│                                   │  Task?  │                 │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-001 sync-is-first-step         │ ✅      │ T027, T032      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-002 record-all-incoming        │ ✅      │ T025, T029      │ Account 0, per spec     │
│                                   │         │                 │ Assumptions             │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-003 no-outgoing                │ ✅      │ T017, T018      │ "out": false assertion  │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-004 one-confirmation           │ ✅      │ T017, T018      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-005 record-fields              │ ✅      │ T011, T025      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-006 exact-amount               │ ✅      │ T015, T025      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-007 tz-independent-time        │ ✅      │ T010, T025      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-008 txid-identity-and-sum      │ ✅      │ T024, T025,     │                         │
│                                   │         │ T034            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-009 never-modify               │ ✅      │ T012, T014,     │                         │
│                                   │         │ T034            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-010 no-change-when-nothing-new │ ✅      │ T034            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-011 no-new-message             │ ✅      │ T035, T039      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-012 count-message              │ ✅      │ T027, T032      │ See L3                  │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-013 keep-on-interrupt          │ ✅      │ T040, T043      │ See U4                  │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-014 resume-completes           │ ✅      │ T040            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-015 errors-no-traceback        │ ✅      │ T041, T042,     │                         │
│                                   │         │ T044, T045      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-016                            │ ✅      │ T013, T014,     │                         │
│ persist-create-never-recreate     │         │ T026            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-017 wallet-url                 │ ✅      │ T021, T022,     │                         │
│                                   │         │ T027            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-018 password-handling          │ ✅      │ T017, T021,     │                         │
│                                   │         │ T027, T041      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ FR-019 say-transactions           │ ✅      │ T041, T046      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ SC-001 all-incoming-recorded      │ ✅      │ T025, T017      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ SC-002 exact-12dp                 │ ✅      │ T025            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ SC-003 idempotent                 │ ✅      │ T034            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ SC-004 interruption-equivalence   │ ✅      │ T040            │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ SC-005 failed-runs-clean          │ ✅      │ T041, T042      │                         │
├───────────────────────────────────┼─────────┼─────────────────┼─────────────────────────┤
│ SC-006 under-5s                   │ ✅      │ T036            │                         │
└───────────────────────────────────┴─────────┴─────────────────┴─────────────────────────┘

Constitution Alignment Issues: none. The concerns from the first pass are cleared:
- Principle I: make_wallet lives in orchestration, and the CLI is barred from importing primitives.Principle III: amounts are integer piconero, which v1.2.0 allows.Principle IV: fetching, transforming and saving are separate functions.Principle V: fakes plus a redirected HOME; database tests use in-memory SQLite or tmp_pathfiles.Principle VI: rows are insert-only, with one commit per window.
- Principle VII: all five quality checks are in T048.

Unmapped Tasks: T047 (README) is polish. Setup tasks T001–T006 serve Principle VII and Constraints.

Metrics
- Total requirements: 25 (19 FR + 6 SC)
- Total tasks: 49
- Coverage: 100% (25/25)
- Ambiguity count: 0
- Duplication count: 0 (FR/SC restatements accepted last pass)
- Critical issues: 0

Next Actions

- Implementation is not blocked. There are no CRITICAL or HIGH findings, so you could start /speckit-implement.
- Worth fixing first: the three MEDIUM items are small edits to tasks.md.
  - I6: a one-line wording fix.
  - U4: give T040's partial-window case a concrete trigger.
  - G3: add a test task for a second run started during another, in Phase 5. Adding it renumbers the later tasks.
- LOW items can be left or picked up during implementation.

Would you like me to suggest concrete remediation edits for the top 3 issues (I6, U4, G3)?

## Analysis Pass 2 Follow up Prompt
Apply these analyze fixes to tasks.md and research.md: I6, U4, and G3 as
recommended; L1 by removing the [P] from T005; L2 as recommended.
For L3, add one line to spec FR-012 stating that it applies to runs that
complete successfully. Change nothing unrelated.

## What Came Back
I applied all six fixes. tasks.md now has 50 tasks (T001–T050). The new test is T041, so later tasks moved up by one, and every reference to them is updated.

- I6: the US2 independent test now uses "the same fake and a tmp_path database file."
- U4: the partial-window case (now in T040) has a concrete trigger. The third window holds a normal entry plus one at 9,223,372,036,854,775,808 piconero, which overflows on insert. The test expects RunError, neither of that window's rows stored, and windows 1–2 kept.
- G3: new T041 writes tests/integration/test_concurrent_run.py:
  - A second connection holds the write lock with BEGIN IMMEDIATE while run() runs against the same tmp_path database.
  - The test expects RunError with cannot write to database (or cannot read database if the lock hits at open), and existing rows intact afterwards.
  - To keep it fast, T014's open_database gains a timeout: float = 5.0 parameter. The test passes 0.1 seconds.
  - T041 is added to the US3 dependency range and the parallel example.
- L1: removed [P] from T005. I also changed the Setup dependency line from "T003, T004 and T005 in parallel" to "T003 and T004 in parallel; T005 after T003," which otherwise would still have said it was parallel.
- L2: research.md R6 now says the account-0 limit is intended and points to the spec's Assumptions.
- L3: spec.md FR-012 gains one sentence: "This applies to runs that complete successfully; failed runs follow FR-015."

Nothing else changed. All six analysis findings are now addressed, so the next step is /speckit-implement. You could run /speckit-analyze once more first to confirm a clean pass.
