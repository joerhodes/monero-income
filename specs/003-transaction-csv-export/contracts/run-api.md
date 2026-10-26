# Contract: `run()` changes for feature 003

Additions to [feature 002's run-api](../../002-usd-valuation/contracts/run-api.md).

```python
@dataclass(frozen=True)
class CliOptions:
    ...                                       # feature 001/002 fields unchanged
    reports_path: str | None = None           # new

@dataclass(frozen=True)
class ExportSummary:                          # new; exported from monero_income.orchestration
    path: Path                                # absolute path of xmr_income.csv
    transactions: int                         # data rows written

@dataclass(frozen=True)
class RunResult:
    recorded: int
    imported: ImportSummary | None = None
    pricing: PricingSummary = field(default_factory=PricingSummary)
    exported: ExportSummary | None = None     # new; always set by a successful run()
```

The `run()` signature is unchanged; no new seams are needed:

- **Reports directory in tests**: the `HOME` fixture redirects the default `~/reports`, and
  tests can pass `CliOptions(reports_path=...)` to choose another directory.
- **Write failures**: tested at the primitive level with row iterables that raise partway,
  and at the `run()` level with a reports path that is a file or an unwritable directory.

## Order

settings → database → sync → import (if requested) → pricing → **read export rows → close
database → write export**.

- Any failure before the export step raises as before. The export is not written (FR-002).
- `ExportWriteError` → `RunError("cannot write export <path>: <reason>. Recorded transactions
  and prices were kept; the previous export was not changed.")` (FR-008).
- `StorageReadError` while reading the rows → feature 001's `cannot read database …` message.
- `KeyboardInterrupt` propagates after the temporary file is removed.
