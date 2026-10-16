# 06 - Decisions for Legacy Code Findings

## Prompt
Update specs/001-sync-incoming-transactions/spec.md with these decisions.
Keep requirements, edge cases, and success criteria consistent with each
other. Do not change anything else.

1. Exclude self transfers when retrieving incoming transactions.
2. A first run with no existing local records creates them.
3. Any error, including invalid settings or unreadable local records, is
   shown as a message with a failure status, never a raw traceback.
4. The password can be supplied without appearing on the command line;
   A password without a username should generate an error.
5. The wallet is specified by its address (URL), not host and port.
6. On a first sync, the user may give an optional start date (UTC);
   transactions before it are not recorded.
7. User-facing messages say "transactions," not "transfers."

## What came back
I updated specs/001-sync-incoming-transactions/spec.md with all seven decisions and changed nothing else.

┌─────┬────────────────────────────────────────┬───────────────────────────────────────────┐
│  #  │                Decision                │              Where it landed              │
├─────┼────────────────────────────────────────┼───────────────────────────────────────────┤
│ 1   │ Self transfers excluded                │ FR-003, edge case, SC-001                 │
├─────┼────────────────────────────────────────┼───────────────────────────────────────────┤
│ 2   │ First run creates the local records    │ FR-016, new edge case, Key Entities       │
├─────┼────────────────────────────────────────┼───────────────────────────────────────────┤
│     │ Every error is a message with a        │ FR-015 (now covers any error in a run),   │
│ 3   │ failure status, never a raw traceback  │ SC-005, new edge case for invalid         │
│     │                                        │ settings                                  │
├─────┼────────────────────────────────────────┼───────────────────────────────────────────┤
│     │ Password can stay off the command      │                                           │
│ 4   │ line; a password without a username is │ FR-018, new edge case, Assumptions        │
│     │  an error                              │                                           │
├─────┼────────────────────────────────────────┼───────────────────────────────────────────┤
│ 5   │ Wallet specified by URL                │ FR-017; the unreachable-wallet edge case  │
│     │                                        │ now names the URL                         │
├─────┼────────────────────────────────────────┼───────────────────────────────────────────┤
│ 6   │ Optional start date (UTC) on the first │ New FR-020, FR-002, two new edge cases,   │
│     │  sync                                  │ SC-001, Key Entities                      │
├─────┼────────────────────────────────────────┼───────────────────────────────────────────┤
│ 7   │ Messages say "transactions," not       │ New FR-019                                │
│     │ "transfers"                            │                                           │
└─────┴────────────────────────────────────────┴───────────────────────────────────────────┘

Rules I added so the start date stays consistent with the other requirements:
- The start date is saved with the local records and applied to every later sync. Otherwise, an interrupted first sync or a first sync that recorded nothing would make the next run record everything before the date. That would break FR-014 and SC-003.
- A start date given on a later run must match the saved one, or the run fails with an error. This lets the user retry a failed first run with the same command without getting an error.
- "First sync" means the run that creates the local records. A transaction at exactly 00:00:00 UTC on the start date is recorded.
- Local records that exist but can't be read are never treated as a first run. This keeps decision 2 from ever overwriting damaged data.

I didn't add these decisions to the Clarifications log, since you asked me not to change anything else. The constitution's "wallet RPC is local" rule still conflicts with the spec and needs amending before /speckit-plan.
