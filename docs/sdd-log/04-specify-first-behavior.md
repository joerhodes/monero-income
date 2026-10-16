# 04 - Specify First Behavior

**Command:** /speckit-specify
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-12

## Prompt
/speckit-specify monero-income is a command-line tool that records a Monero
wallet's incoming mining transactions locally, so they can later be valued in
USD and reported. This feature covers only retrieving and recording incoming
transactions from the wallet. USD pricing, CSV output, and on-screen
summaries are separate, later features and are out of scope here.

Behaviors:
- Running a sync records every incoming wallet transaction that isn't already
  recorded.
- Running a sync again with no new transactions changes nothing.
- If a sync is interrupted, already recorded transactions are kept, and the
  next sync records the rest.
- Outgoing transactions are not recorded.
- If no new transactions are found, a message is displayed to the user before
  the run continues.
- Any error encountered during the sync is reported to the user, and the
  application exits.
- Recorded transactions persist locally between runs.

Each recorded transaction keeps its transaction id, block height, XMR amount
at full precision, and the exact moment it occurred, independent of time zone.

## What came back
I wrote the spec for the sync feature. It passed every item on the quality checklist on the first pass, and it has no [NEEDS CLARIFICATION] markers. No branch was created because there's no git extension hook, so you're still on main.

- Feature directory: specs/001-sync-incoming-transactions/
- Spec: specs/001-sync-incoming-transactions/spec.md
- Checklist: specs/001-sync-incoming-transactions/checklists/requirements.md

What it covers:
- Three user stories:
  - P1: record incoming transactions.  
  - P2: re-sync safely, only adding new ones.  
  - P3: recover from interruptions and errors.
- 16 functional requirements and 6 success criteria. Examples: amounts match the wallet exactly
  to 12 decimal places, and re-syncing after an interruption leaves the same records as one  uninterrupted sync.

Calls I made where your description didn't decide (listed in Edge Cases and Assumptions):
1. All incoming transfers are recorded, not only ones identifiable as mining payouts. Your behaviors say "every incoming wallet transaction"; the opening line says "mining transactions."                                                                   
2. Unconfirmed incoming transactions are skipped until they're in a block, since a record needs a block height.                                                                  
3. One record per transaction id. If a transaction pays several subaddresses, it's recorded once with the total the wallet received.                                         
4. Existing records are never modified, even if the wallet later reports a different block height after a chain reorganization.
5. The tool reports how many transactions it recorded when it finds new ones. You only specified the "nothing new" message.
6. One wallet only. How the tool connects to the wallet is decided during planning.

The first three are worth confirming in /speckit-clarify.

Two wording problems in your constitution edits. I haven't changed either:
- Principle I: "the CLI only import orchestration" is missing a word. It probably means "the
  CLI MUST only import orchestration."
- Principle VI: "No operation MUST delete transaction records or overwrite finalized prices" reads as permission rather than a ban. It should be "Operations MUST NOT delete…"

Since that's a wording fix, it would be a PATCH bump to 1.0.1. Your edits otherwise left the version and amended date unchanged.


## Hand edits
Made edit to constitution as recommended.  Saved and committed as 1.0.1.
Installed the git extension for specify.
Manually created branch `001-sync-incoming-transactions`.
Dropped 'mining' from the User description: '...incoming mining transactions...'

## Notes
