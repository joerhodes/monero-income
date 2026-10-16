# Contract: `run()` (orchestration entry point)

All behavior is reachable through `run()`, with no Typer involved (constitution II). The CLI
converts its options into `CliOptions`, supplies a `Reporter`, calls `run()`, and formats the
result.

```python
# monero_income.orchestration

@dataclass(frozen=True)
class CliOptions:
    rpc_url: str | None = None
    username: str | None = None
    db_path: str | None = None

class Reporter(Protocol):
    def warning(self, message: str) -> None: ...

@dataclass(frozen=True)
class SyncResult:
    recorded: int

class RunError(Exception):
    """User-facing failure. str(error) is the complete message, with no 'Error:' prefix."""

def run(
    options: CliOptions,
    reporter: Reporter,
    *,
    config_path: Path | None = None,  # None → ~/.config/monero-income/config.toml, resolved at call time
    wallet_factory: Callable[[Settings], WalletRpc] = make_wallet,
    connect: Callable[[Path], sqlite3.Connection] = open_database,
) -> SyncResult: ...
```

- **Success**: returns `SyncResult`. The CLI prints the matching line from
  [cli.md](cli.md).
- **Failure**: raises `RunError` for every expected failure. Primitive errors are translated
  in orchestration, so the CLI never imports `primitives` (import-linter forbids it).
- **Warnings** (config permissions, unknown keys) go through `reporter.warning` as soon as
  they're found, so they appear even if the run later fails.
- **Wallet factory**: `make_wallet(settings) -> WalletRpc` lives in orchestration and builds
  `HttpWalletRpc(settings.rpc_url, settings.username, settings.password)`. Primitives never
  see `Settings` (constitution I).
- **Default paths**: the default config path and the default `db_path` expand `~` when
  `run()` is called, not at import time, so redirecting `HOME` redirects both.
- **Connection ownership**: `run()` closes the connection it gets from `connect`. Closing an
  in-memory SQLite database discards it, so in-memory connections suit only tests that call
  `run()` once and don't inspect the database afterwards.
- **Test seams**: `config_path`, `wallet_factory`, and `connect` let tests run the whole flow
  with a temporary or absent config file and `FakeWalletRpc`. No network access is needed.
  - Tests that call `run()` more than once, or inspect the database after it, use a `tmp_path`
    database file through the real `open_database`.
  - An autouse fixture in `tests/conftest.py` points `HOME` at `tmp_path`, so no test can
    reach the real config or database.
- The real `connect` (`open_database`) handles the file rules: create the parent directory
  and file when missing, never recreate an unreadable file.
