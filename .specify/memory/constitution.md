
# monero-income Constitution

monero-income is a Python command-line tool that builds weekly and monthly income reports
from a Monero wallet, valuing each payout at its historical USD price.

## Core Principles

### I. Layered Architecture

The codebase is divided into three layers:

- **Primitives**: a library of building blocks for the wallet RPC, the price API, and the
  database.
- **Orchestration**: composes primitives into the application's operations (sync, report
  building).
- **CLI**: the user-facing entry point.

Dependencies MUST point inward only: the CLI MUST only import orchestration,
orchestration may import primitives, and primitives MUST NOT import either outer layer.
These rules MUST be enforced by import-linter contracts; a layering rule that has no
contract is not considered enforced.

Rationale: inward-only dependencies keep the primitives reusable and independently
testable, and keep the CLI replaceable.

### II. Thin CLI

The CLI MUST only parse arguments and format output. It MUST NOT contain business logic,
data access, or computation beyond presentation. All behavior MUST be reachable through a
`run()` function that can be called and tested without Typer.

Rationale: behavior that lives behind a plain function is testable without invoking a CLI
framework, and the CLI stays trivially reviewable.

### III. Exact Money

Monetary and XMR amounts MUST be represented as `Decimal` from the point they enter the
system to the point they are output, and MUST be stored losslessly. `float` MUST NOT be used
for any monetary or XMR value, including intermediate calculations, serialization, and
storage.

Rationale: binary floating point cannot represent decimal currency exactly; rounding errors
in income reports are correctness bugs.

### IV. Separate I/O from Transformation

Functions that fetch or persist data MUST NOT also compute or reshape it. Transformation
logic MUST live in functions that take data in and return data out, with no I/O.

Rationale: pure transformations can be tested exhaustively with plain values; I/O functions
stay small enough to verify against fakes.

### V. Testable Without the Network

Every external service (wallet RPC, price API) MUST sit behind a `typing.Protocol`. Tests
MUST use fakes that implement those protocols and in-memory SQLite for the database. The
test suite MUST NOT make network calls.

Rationale: tests that depend on live services are slow, flaky, and can leak wallet data.

### VI. Data Safety

- Sync MUST be idempotent: running it repeatedly over the same data produces the same
  stored state.
- Sync MUST be interruption-safe: an interrupted sync leaves the database consistent and
  a subsequent run completes correctly.
- Operation MUST NOT delete transaction records or overwrite finalized prices. Provisional prices MAY be refreshed until they are finalized.
- Schema changes MUST ship as explicit migrations, and each migration path MUST be tested
  from every prior released schema version.

Rationale: the database holds the user's financial history; losing or corrupting it is the
worst failure this tool can have.

### VII. Automated Gates

The following gates MUST all pass before a change is merged:

- ruff (lint and format)
- mypy `--strict`
- import-linter
- pytest, meeting the coverage floor set in pyproject.toml

`pyproject.toml` is the single source of truth for tool configuration, including the
coverage floor. This constitution MUST NOT restate tool rules; it requires only that the
gates exist and pass.

Rationale: automated gates make the principles above enforceable rather than aspirational,
and keeping configuration in one place prevents drift.

## Constraints

- **Runtime**: Python 3.13 or newer.
- **Tooling**: the project MUST be managed with uv.
- **Local-first**: the only external dependency at runtime is the price API. The wallet RPC
  and database are local.
- **Private data**: real wallet data and database snapshots MUST NOT be committed to the
  repository. Test fixtures MUST be synthetic.

## Development Workflow

- Features MUST progress through spec → clarify → plan → tasks → analyze → implement.
- Report output is locked by golden-file tests. Any change to report output MUST be stated
  in a spec, and the affected golden files MUST be updated in the same change.

## Governance

This constitution supersedes other project practices. Deviating from a principle requires
amending this constitution first; a plan or implementation MUST NOT justify a deviation
without a prior amendment.

- **Amendments**: proposed as a change to this file, with the rationale and any migration
  impact on existing specs, plans, or code stated in the change.
- **Versioning**: semantic versioning. MAJOR for removing or redefining a principle; MINOR
  for adding a principle or section or materially expanding guidance; PATCH for
  clarifications and wording.
- **Compliance**: every plan MUST check itself against these principles, and every change
  MUST be reviewed for compliance before merge. The automated gates in Principle VII are the
  minimum check, not the whole check.

**Version**: 1.0.1 | **Ratified**: 2026-10-11 | **Last Amended**: 2026-10-12
