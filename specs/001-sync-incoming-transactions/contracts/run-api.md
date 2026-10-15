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
    config_path: Path = DEFAULT_CONFIG_PATH,
    wallet_factory: Callable[[Settings], WalletRpc] = HttpWalletRpc.from_settings,
    connect: Callable[[Path], sqlite3.Connection] = open_database,
) -> SyncResult: ...
```

- **Success**: returns `SyncResult`. The CLI prints the matching line from
  [cli.md](cli.md).
- **Failure**: raises `RunError` for every expected failure. Primitive errors are translated
  in orchestration, so the CLI never imports `primitives` (import-linter forbids it).
- **Warnings** (config permissions, unknown keys) go through `reporter.warning` as soon as
  they're found, so they appear even if the run later fails.
- **Test seams**: `config_path`, `wallet_factory`, and `connect` let tests run the whole flow
  with a temporary or absent config file, `FakeWalletRpc`, and an in-memory SQLite
  connection. No network access is needed.
- The real `connect` (`open_database`) handles the file rules: create the parent directory
  and file when missing, never recreate an unreadable file.
