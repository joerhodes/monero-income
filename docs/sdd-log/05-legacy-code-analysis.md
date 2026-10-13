# 05 - Legacy Code Analysis

## Motivation

For the process up to this point, I have been relying on my memory and my own research of the existing implementation to gather information for the prompts.   Going forward I will use another instance Claude CLI to analize the existing, legacy code base.  

One reason to make this change it that it will be more representative of how a full rewrite might actually in todays AI environment.  Either all the original specs and change requests would be used to manually produce a new spec, or AI would be asked to analyze the exist code to gather the information for a new spec.

Also, the current process feels burdensome for a solo developer.  And using AI to gather the information should speed up and lighten the process going forward.

## Prompt
I'm rewriting this tool as a new project using spec-driven development.
Analyze this codebase so I can write specs and implementation plans for the
rewrite. Do not modify anything in this repository. Write output only to
~/Projects/monero-income/docs/sdd-log/extraction/.

Never copy values from any config or secrets file (URLs, usernames,
passwords, keys). Describe config keys and their purpose only.

For reference, read:
- ~/Projects/monero-income/specs/001-sync-incoming-transactions/spec.md
- ~/Projects/monero-income/docs/sdd-log/02-behavior-inventory.md
The inventory shows the writing style I want for behavior statements:
testable, user-observable, no implementation terms.

Produce these files:

1. implementation-facts.md: Python version and dependencies; package
   layout; database schema, column types, keys, and migrations; wallet RPC
   calls, parameters, authentication, and how responses become records;
   price API endpoints, rate-limit and error handling; config file format,
   location, and keys; CLI commands, flags, exit codes, and user-facing
   messages; how CSV rows and weekly/monthly summaries are computed.

2. sync-spec-check.md: compare spec 001 against the code. List each place
   where the code's actual behavior differs from the spec or isn't covered
   by it.

3. behaviors-pricing.md, behaviors-csv.md, behaviors-summaries.md:
   user-observable behaviors for each area, in the inventory's style,
   including error and edge-case behavior.

4. tests-coverage.md: what the existing tests cover, and gaps relevant to
   writing golden-file tests.

5. oddities.md: anything that looks unintentional, inconsistent, or
   buggy.

Cite file:line for every item. Mark anything inferred rather than read
directly as (inferred). Keep each file focused; prefer short statements
over prose.

## What Came Back
I've written all seven files to ~/Projects/monero-income/docs/sdd-log/extraction/. Every item cites file:line in the legacy repo, and anything I couldn't read directly from the code is marked (inferred).

What I checked beyond reading the code: I ran the 98 existing tests (all pass) andran the legacy functions on sample data in a temp folder. Items confirmed that wayare marked "verified".

Findings you'll most likely want in the specs:
- Payments to several subaddresses are under-recorded. The wallet returns one entry  per subaddress, and the code keeps only the first one for each transaction id.  Spec 001 (FR-008) requires the total. Verified.
- Sync can miss transactions for good. It only asks the wallet for blocks above the  highest height it has stored. Another transaction at that same height, or one  that appears lower after a rescan or chain reorganization, is never fetched  (inferred from how the wallet handles its height filter).
- The first run crashes with the default settings. The tool never creates the  folder for its default database file. Verified.
- The code doesn't match spec 001 on reporting. It never tells the user how many  transactions it recorded (FR-012). 
- Database errors, bad settings files and unknown time zones crash with a traceback instead of an error message.
- The behavior inventory doesn't match the code in four places:
  - The default time zone is fixed to America/Chicago, not the machine's.
  - An unpriced transaction gets an empty usd_price but TBD (not blank) in usd_value.
  - Months with no transactions are left out of the summaries.  
  - The price-failure message counts days, not transactions.
- Some output formats need deciding before you write golden files. XMR amounts are  written without trailing zeros, and very small amounts come out in scientific  notation (e.g. 1E-7). Verified. 
- --since filters by UTC date while everything else  uses local dates, so a row dated before the --since date can appear. Verified.
- The tests can't serve as golden files yet. Nothing runs the whole command or  checks screen output. The CSV tests pass in pre-formatted dates, so the real date  formatting is never tested. Some tests use random data.

Things to know:
- Config values: I read only key names and purposes from config.toml.example. Its values are the same as the defaults built into the code. The one specific value in the docs is the default wallet port (18088), which I took from the source code. Both web-address defaults are described in words rather than copied.
- Repo changes: none to tracked files (git status is clean). However, one run I did to check behavior refreshed two Python cache files, under src/*/__pycache__/. They're gitignored and Python recreates them on its own.

Files are in ~/Projects/monero-income/docs/sdd-log/extraction/:
- implementation-facts.md
- sync-spec-check.md
- behaviors-pricing.md
- behaviors-csv.md
- behaviors-summaries.md
- tests-coverage.md
- oddities.md


## Notes

This analysis shows how even for a small solo project, memory can deviate from the actual code.   So this is a strong indication that an AI guided analysis would almost always be the better path.

This analysis also found bugs in the original code that might have been copied over to the rewrite.

Also, note that AI interpreted "analyze" in a manner that it decided to run tests.  This suggest that when asking for a code base analysis, a list of allowed actions might need to be included.

### Findings

| Finding | Keep or change? |
|---|---|
| Payments to several subaddresses are under-recorded | Change: already in spec 001 |
| Sync can miss transactions for good | Change: already in spec 001 |
| First run crashes with defaults | Change: fix |
| Code doesn't match spec 001 on reporting | Change: already in spec 001 |
| Database errors crash with a traceback | Change: fix |
| Bad settings files crash with a traceback | Change: fix |
| Unknown time zones crash with a traceback | Change: fix |
| Default time zone is fixed to America/Chicago | Change: already in spec 001 |
| Unpriced transaction gets an empty usd_price but TBD (not blank) in usd_value | Keep: an unpriced transaction shows TBD as its USD value, so a reader can see it's pending, not zero.  |
| Months with no transactions are left out of the summaries | Keep |
| The price-failure message counts days, not transactions | Keep |
| XMR amounts are  written without trailing zeros | Change |
| Very small XMR amounts come out in scientific notation | Change |
| `--since` filters by UTC date | Keep |
