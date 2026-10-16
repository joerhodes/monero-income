# 11 - Implement Phase 1 and Phase 2

**Command:** /speckit-implement
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-16

## Prompt
/speckit-implement Phase 1 (Setup) and Phase 2 (Foundational) only. Stop
after Phase 2 so I can review, run the gates, and commit.

## What Came Back
Phases 1 and 2 are done: T001–T023 are marked [X] in tasks.md, and I've stopped before Phase 3. Nothing is committed.

All five gates pass on my run:

┌──────────────────────────────────┬───────────────────────────────────────┐
│               Gate               │                Result                 │
├──────────────────────────────────┼───────────────────────────────────────┤
│ ruff check / ruff format --check │ pass                                  │
├──────────────────────────────────┼───────────────────────────────────────┤
│ mypy (strict, src + tests)       │ no issues in 28 files                 │
├──────────────────────────────────┼───────────────────────────────────────┤
│ lint-imports                     │ 2 contracts kept                      │
├──────────────────────────────────┼───────────────────────────────────────┤
│ pytest                           │ 77 passed, coverage 93.6% (floor 90%) │
└──────────────────────────────────┴───────────────────────────────────────┘

Phase 2 provides the error, model and RunError modules, the schema and storage code, the wallet
response parser, the HTTP wallet client, config reading, settings resolution and the test
fake. Phase 3 builds on these. The HTTP client is tested through a real Digest-auth handshake
using httpx's mock transport, with no sockets opened.

Places where I went beyond the task text:
- allow_indirect_imports = true on the "cli must not import primitives" contract. Without it, import-linter flags the intended route (CLI → orchestration → primitives) as a violation.
- A placeholder src/monero_income/cli.py containing only a docstring. The import-linter contracts fail if the module doesn't exist, and T032 replaces it in Phase 3. Until then, the monero-income console script has no main() and won't run.
- ruff excludes .specify/, specs/ and docs/. Otherwise it lints Spec Kit's own scripts and tries to reformat the Python examples inside the spec markdown.
- HttpWalletRpc has a close() method, so run() can release the HTTP client in Phase 3.
- Python 3.14.8. uv picked the 3.14 install on your machine, which satisfies >=3.13.

Things to know when reviewing:
- For the database tests (T012, T013), I wrote the tests and the code together instead of confirming the tests failed first. Every other test file was run and failed before its implementation existed.
- Your editor's Pyright warnings (unresolved pytest, "| unions need Python 3.10") come from it using the system Python 3.9. Pointing it at .venv clears them. mypy in the project environment is clean.

Before committing: the new pyproject.toml, uv.lock, src/ and tests/ are untracked, and .gitignore and tasks.md are modified. docs/sdd-log/11-implement-phase1-2.md is also untracked; that's from your own logging, and I haven't touched it.

## Notes
All gates run cleanly.
All code and tests pass an initial sniff test - nothing jumps out.
Database test T012: I sabotaged a couple of implementation and reran tests to ensure failures were records.
Database test T013: I verified that errors are reported if file creation is commented out.
Pinned Python to 3.13 for project.
