# Implementation Plan: USD Valuation of Recorded Transactions

**Branch**: `002-usd-valuation` | **Date**: 2026-10-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-usd-valuation/spec.md`

## Summary

After a successful sync, each run prices every UTC day that has recorded transactions and no
final price. It calls CoinGecko `/coins/{id}/history`, one paced request per day, oldest
first. It skips days more than 364 days old, and stores each price exactly (decimal text)
with a status (provisional until 1 hour after the day ends, then final on the next lookup)
and a source.
- **Price-source problems** (rate limit after one retry, rejected key, unreachable source)
  stop pricing for the run without failing it.
- **Storage errors** fail it.
- **USD values** are computed exactly from amount × price on demand and never stored.
- **Optional (P3):** `--import-prices CSV` fills old unpriced days with final prices before
  lookups.

The feature follows feature 001's stack, layers, config, error handling and test conventions;
only the differences are listed here.

**Resolved since the first draft** (2026-10-17):
- SC-012 was removed and SC-007 revised; the default interval with a key is a conservative
  2.5 s (research R1).
- The key type (`demo`/`pro`) is configured with the key and selects the header and the default
  base URL. Both can be overridden on the command line (research R3).
- `error_code` 10012 was confirmed by a manual request.

## Technical Context

**Language/Version, tooling, gates**: unchanged from feature 001

**New dependencies**: none (httpx, stdlib `csv`, `decimal`, `json`)

**Storage**: schema version 2 adds the `daily_prices` table and two immutability triggers
([data-model.md](data-model.md))

**External service**: CoinGecko `/coins/{id}/history`, USD. Optional key; its type selects
`x-cg-demo-api-key` or `x-cg-pro-api-key` (legacy) and the default host
([contracts/price-source.md](contracts/price-source.md))

**Testing**: `FakePriceSource` behind a `PriceSource` Protocol; `httpx.MockTransport` for the
client; injected `clock` and `sleep`, so there are no real waits; a migration test from a
version-1 database

**Performance Goals**: none for run duration (SC-012 was removed). SC-007: default intervals
of 2.5 s with a key and 6.0 s without stay within the published limits, and
`min_request_delay` overrides them (research R1).

**Constraints**:
- No float for prices or values; JSON is decoded with `parse_float=Decimal`.
- Decimal math runs under a local context that traps `Inexact`.
- The API key never appears in output.
- Final prices are immutable in code and in the database.

**Scale/Scope**: at most 365 requestable days per run; one request per day; one commit per
price

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.* Checked against
constitution v1.2.0.

| Principle | Status | How the design complies |
|-----------|--------|-------------------------|
| I. Layered architecture | ✅ | `primitives/price_source.py` (HTTP), `primitives/price_parse.py` (pure parsing), `primitives/prices_db.py` (storage), `primitives/price_import_file.py` (file read); `orchestration/pricing.py` and `orchestration/price_import.py`; the CLI only gains `--import-prices`. Existing import-linter contracts cover the new modules. |
| II. Thin CLI | ✅ | The CLI passes `import_prices` in `CliOptions` and formats `RunResult` into the lines in [contracts/cli.md](contracts/cli.md). Pacing, retry, settling and counting live in orchestration. |
| III. Exact money | ✅ | Prices are `Decimal` from JSON (`parse_float=Decimal`) and CSV (validated text), and stored as decimal text. `usd_value` uses integer piconero × `Decimal` under an `Inexact`-trapping context (research R4). |
| IV. Separate I/O from transformation | ✅ | The client makes one HTTP request and returns raw outcomes. Parsing, cutoff, settling, ordering, import validation and selection are pure functions. The retry and pacing loop is orchestration. |
| V. Testable without the network | ✅ | `PriceSource` Protocol and fake; `MockTransport`; injected `clock`/`sleep`; pytest-socket. |
| VI. Data safety | ✅ | One commit per price (an interruption keeps them); final prices protected by the conditional upsert and a `BEFORE UPDATE` trigger; deletes blocked; migration 1 → 2 tested from a version-1 database; import validated in full, then one transaction. |
| VII. Automated gates | ✅ | Unchanged; the 90% coverage floor applies to the new modules. |
| Constraints | ✅ | The price API is the only external runtime dependency, as the constitution allows. Synthetic fixtures only. |
| Workflow / golden files | ✅ | The run's status lines aren't report output; no golden files change. |

**Post-design re-check**: unchanged; no violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-usd-valuation/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── cli.md            # --import-prices, new output lines, exit codes
│   ├── config.md         # coingecko_api_key(+_type), coingecko_url, coin_id, min_request_delay
│   ├── price-source.md   # PriceSource Protocol, request, response classification
│   ├── import-csv.md     # CSV format and processing
│   └── run-api.md        # RunResult, new run() seams
└── tasks.md              # /speckit-tasks
```

### Source Code (changes to feature 001's layout)

```text
src/monero_income/
├── cli.py                          # + --import-prices, --coingecko-api-key(-type); formats RunResult
├── orchestration/
│   ├── run.py                      # sync → import → pricing; RunResult; make_price_source
│   ├── settings.py                 # + new keys, min_request_delay, import_prices
│   ├── pricing.py                  # NEW: pacing, retry-once, stop rules, summary
│   ├── price_import.py             # NEW: import step (validate → select → insert)
│   └── valuation.py                # NEW, pure: history_cutoff, plan_lookups, settled_at,
│                                   #   price_status, default_delay, usd_value, select_imports
└── primitives/
    ├── errors.py                   # + PriceRateLimitedError, PriceKeyRejectedError,
    │                               #   PriceUnavailableError, ImportFileError
    ├── models.py                   # + DailyPrice, PriceNeed, ImportRow
    ├── migrations.py               # + step 2 (daily_prices, triggers)
    ├── prices_db.py                # NEW: price_needs, upsert_price, insert_imported, priced_days
    ├── price_source.py             # NEW: PriceSource Protocol, CoinGeckoPriceSource (httpx)
    ├── price_parse.py              # NEW, pure: parse_history_price, Price/NoPrice/OutsideHistory
    └── price_import_file.py        # NEW: read_import_file (I/O) + parse_import (pure)

tests/
├── fakes/price_source.py           # FakePriceSource
├── fakes/clock.py                  # FakeClock, RecordingSleep
├── unit/                           # valuation, price_parse, parse_import, migration 1→2
├── adapters/                       # CoinGecko client via MockTransport; prices_db; import file
├── integration/                    # run() pricing scenarios, import scenarios (tmp_path DBs)
└── cli/                            # new lines, warnings, --import-prices errors
```

**Structure Decision**: same single package and layers as feature 001. Pricing has its own
orchestration and primitives modules, so `sync` stays unchanged.

## Complexity Tracking

No violations.
