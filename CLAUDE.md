# CLAUDE.md

monero-income: a Python CLI that syncs a Monero wallet's incoming
transactions, values them in USD, writes a transaction CSV export, and
shows income summaries. Built with Spec Kit; principles are in
`.specify/memory/constitution.md`, and each feature's spec and plan are
in `specs/`.

## Commands

- `uv run pytest` (coverage floor in pyproject.toml)
- `uv run ruff check` and `uv run ruff format --check`
- `uv run mypy`
- `uv run lint-imports`

All must pass before a change is merged.

## Rules

- `docs/sdd-log/` is a human review log of SDD prompts and decisions. Do
  not read it or use it as context.
- Do not add performance or timing success criteria unless the user asks
  for them; this is a small personal tool.
- `tests/golden/` holds reviewed expected output. Never edit a golden
  file to make a test pass; fix the code, or stop and explain why the
  golden file seems wrong.
- Tests must never touch real user data, config, or the network.
- During planning steps, change only planning artifacts, not code or
  dependencies.
- When a feature is complete, set its spec's Status to `Implemented`
  before merging.
