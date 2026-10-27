# Contract: `run()` and rendering API for feature 004

Additions to [feature 003's run-api](../../003-transaction-csv-export/contracts/run-api.md).

```python
@dataclass(frozen=True)
class CliOptions:
    ...                                       # feature 001–003 fields unchanged
    timezone: str | None = None               # new

@dataclass(frozen=True)
class PeriodFigures:                          # new; one row of a summary, or its total
    label: str                                # "2026-W44", "2026-10", "2026", or "Total"
    piconero: int                             # exact XMR, all transactions
    usd: Decimal                              # exact, unrounded; priced transactions only
    provisional: bool                         # includes a provisional price
    unpriced: bool                            # leaves out an unpriced transaction

@dataclass(frozen=True)
class Summary:                                # new
    title: str                                # "Weekly Summary", "Monthly Summary", "Annual Summary"
    periods: tuple[PeriodFigures, ...]        # oldest first; 26, 12, or 4
    total: PeriodFigures                      # label "Total"

@dataclass(frozen=True)
class IncomeSummaries:                        # new; exported from monero_income.orchestration
    weekly: Summary
    monthly: Summary
    annual: Summary
    transactions: int                         # all recorded transactions; 0 → the message

@dataclass(frozen=True)
class RunResult:
    recorded: int
    imported: ImportSummary | None = None
    pricing: PricingSummary = field(default_factory=PricingSummary)
    exported: ExportSummary | None = None
    summaries: IncomeSummaries | None = None  # new; always set by a successful run()

class SummaryError(RunError):                 # new; FR-018 (research R10)
    result: RunResult                         # sync/import/pricing/export results; summaries=None

def render_summaries(summaries: IncomeSummaries, width: int | None) -> list[str]:
    """Pure. The lines after the blank line (summaries.md); width None = not a terminal.

    Raises SummaryDataError on a malformed IncomeSummaries."""

def summary_lines(result: RunResult, width: int | None) -> list[str]:
    """The guarded rendering stage: render_summaries(result.summaries, width), complete.

    Any Exception becomes SummaryError(message, result=result)."""
```

`IncomeSummaries`, `Summary`, `PeriodFigures`, `SummaryError`, `render_summaries` and
`summary_lines` are exported from `monero_income.orchestration` for the CLI.

`run()` gains one keyword-only seam, `summary_reader`:

```python
def run(
    ...,                                                  # feature 001–003 parameters unchanged
    summary_reader: Callable[[sqlite3.Connection], Sequence[ExportRecord]] = export_records,
) -> RunResult: ...
```

Its default is the same read the export uses. Tests replace it to inject failures at the
reading and computing stages (research R10).

Other test needs are covered without new seams:
- **Time zone in tests**: pass `CliOptions(timezone="America/New_York")`. For the machine's
  zone, a fixture sets `TZ` and calls `time.tzset()` (research R2).
- **Today**: from the existing `clock` seam.

## Order

1. Settings, then **load the time zone** (`UnknownTimeZoneError` → `RunError` before
   syncing).
2. Database, sync, import (if requested), pricing.
3. Read the export's records. Then **read the summary records** with `summary_reader`, in the
   same snapshot (research R1). A failure of this second read is caught and kept; step 5 is
   then skipped and `run()` raises once the export is written. Then close the database.
4. Write the export.
5. **Build the summaries** from the summary records.
6. Return `RunResult(..., exported=..., summaries=...)`.

Failures:
- **Before step 4**: any failure other than the summary read raises as in feature 003. No
  export is written and no summaries are built.
- **Reading or computing** (the kept read failure, or any `Exception` from step 5): `run()`
  raises `SummaryError` carrying the result of steps 1–4, after the export is written. Its
  message is the one in [cli.md](cli.md).
- **Rendering**: `summary_lines` raises `SummaryError` carrying the result it was given.
- **`KeyboardInterrupt`**: propagates at any step, as before.
