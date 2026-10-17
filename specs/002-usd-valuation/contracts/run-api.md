# Contract: `run()` changes for feature 002

These are additions to [feature 001's run-api](../../001-sync-incoming-transactions/contracts/run-api.md).

```python
@dataclass(frozen=True)
class CliOptions:
    rpc_url: str | None = None
    username: str | None = None
    db_path: str | None = None
    import_prices: str | None = None          # new

@dataclass(frozen=True)
class RunResult:                              # replaces SyncResult
    recorded: int
    imported: ImportSummary | None            # None when --import-prices wasn't given
    pricing: PricingSummary

def run(
    options: CliOptions,
    reporter: Reporter,
    *,
    config_path: Path | None = None,
    wallet_factory: Callable[[Settings], WalletRpc] = make_wallet,
    price_source_factory: Callable[[Settings], PriceSource] = make_price_source,   # new
    connect: Callable[[Path], sqlite3.Connection] = open_database,
    clock: Callable[[], datetime] = utc_now,                                       # new
    sleep: Callable[[float], None] = time.sleep,                                   # new
) -> RunResult: ...
```

- **Order**: settings → database → sync → import (if requested) → pricing. A failure before
  pricing stops the run as in feature 001; pricing never starts (FR-002).
- **Price-source problems** don't raise. They set `pricing.stopped` and go to
  `reporter.warning` (FR-009).
- **Storage and import-file errors** raise `RunError` (FR-020, FR-025).
- **Test seams**: `clock` and `sleep` make settling, the history cutoff, pacing and backoff
  deterministic. Tests pass a fake clock and a recording `sleep`, so no test waits in real
  time.
- **`SyncResult` is renamed `RunResult`.** Feature 001's tests and CLI that construct it are
  updated in the same change.
