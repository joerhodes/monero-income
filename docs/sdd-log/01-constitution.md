# 01 — Constitution

**Command:** /speckit-constitution
**Spec Kit:** v1.1.4.dev0 · **Date:** 2026-10-11

## Prompt
/speckit-constitution Create the constitution for monero-income, a Python CLI
that builds weekly/monthly income reports from a Monero wallet using historical
USD prices. Principles:

1. Layered architecture: a primitives library (wallet RPC, price API, database),
   an orchestration layer, and a thin CLI. Dependencies point inward only;
   enforced by import-linter contracts.
2. Thin CLI: the CLI parses arguments and formats output only. All behavior is
   reachable through a run() function callable and testable without Typer.
3. Exact money: monetary and XMR amounts are Decimal end to end and stored
   losslessly. Never float.
4. Separate I/O from transformation: functions that fetch or persist data do not
   also compute or reshape it.
5. Testable without the network: every external service sits behind a
   typing.Protocol. Tests use fakes and in-memory SQLite; the test suite never
   makes network calls.
6. Data safety: sync is idempotent and interruption-safe, never destroys
   existing data, and schema changes ship as explicit, tested migrations from
   any prior released schema.
7. Automated gates: ruff (lint + format), mypy --strict, import-linter, and
   pytest with a 90% coverage floor must all pass. pyproject.toml is the
   source of truth for tool rules; the constitution does not restate them.

Constraints: Python 3.13+, managed with uv. Local-first: the only external
dependency at runtime is the price API. Real wallet data and database snapshots
are never committed.

Workflow: features go spec → clarify → plan → tasks → analyze → implement.
Report output is locked by golden-file tests; any change to output must be
stated in a spec, and the golden files are updated in the same change.
Deviating from a principle requires amending this constitution first.


## What came back
Got back v1.0.0 of `.specify/memory/constitution.md`.

## Hand edits
- Specified that the CLI can only import orchestration.
- Updated Data Safety to allow provisional prices to be updated.
- Updated code coverage to use value specified in `pyproject.toml`.

## Notes
- Code coverage is expected to be set to 90% in `pyproject.toml`.
