"""run(): the entry point for one full run of the tool. Testable without Typer."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from monero_income.orchestration.errors import RunError
from monero_income.orchestration.settings import (
    CliOptions,
    Settings,
    default_config_path,
    resolve_settings,
)
from monero_income.orchestration.sync import sync
from monero_income.primitives.config_file import read_config
from monero_income.primitives.database import open_database
from monero_income.primitives.errors import (
    ConfigFileError,
    SchemaTooNewError,
    StorageError,
    StorageReadError,
    StorageWriteError,
    WalletError,
    WalletLoginError,
    WalletResponseError,
    WalletRpcError,
    WalletUnreachableError,
)
from monero_income.primitives.wallet_rpc import HttpWalletRpc, WalletRpc


class Reporter(Protocol):
    def warning(self, message: str) -> None: ...


@dataclass(frozen=True)
class SyncResult:
    recorded: int


def make_wallet(settings: Settings) -> WalletRpc:
    return HttpWalletRpc(settings.rpc_url, settings.username, settings.password)


def run(
    options: CliOptions,
    reporter: Reporter,
    *,
    config_path: Path | None = None,
    wallet_factory: Callable[[Settings], WalletRpc] = make_wallet,
    connect: Callable[[Path], sqlite3.Connection] = open_database,
) -> SyncResult:
    """Run once: resolve settings, open the database, sync.

    ``config_path`` defaults to ``~/.config/monero-income/config.toml``, expanded
    at call time. Every expected failure is raised as ``RunError``;
    ``KeyboardInterrupt`` propagates.
    """
    path = config_path if config_path is not None else default_config_path()
    try:
        raw = read_config(path)
    except ConfigFileError as error:
        raise RunError(f"cannot read config file {error}") from error
    settings, warnings = resolve_settings(options, raw, path)
    for warning in warnings:
        reporter.warning(warning)

    try:
        conn = connect(settings.db_path)
        try:
            wallet = wallet_factory(settings)
            try:
                recorded = sync(conn, wallet)
            finally:
                close = getattr(wallet, "close", None)
                if callable(close):
                    close()
        finally:
            conn.close()
    except (StorageError, WalletError) as error:
        raise _run_error(error, settings) from error
    return SyncResult(recorded=recorded)


def _run_error(error: StorageError | WalletError, settings: Settings) -> RunError:
    """The user-facing message for a primitive error (contracts/cli.md).

    Messages are built from the database path, the wallet URL (which can't hold
    credentials), and the error's own text, never from the password.
    """
    db = settings.db_path
    match error:
        case SchemaTooNewError():
            return RunError(
                f"database {db} was written by a newer version of monero-income"
                f" (schema {error.found})"
            )
        case StorageReadError():
            return RunError(f"cannot read database {db}: {error}. The file was not changed.")
        case StorageWriteError():
            return RunError(
                f"cannot write to database {db}: {error}."
                " Transactions recorded before this error were kept."
            )
        case WalletUnreachableError():
            return RunError(f"cannot reach the wallet at {settings.rpc_url}: {error}")
        case WalletLoginError():
            return RunError(
                f"the wallet at {settings.rpc_url} rejected the login; check username and password"
            )
        case WalletRpcError():
            return RunError(f"the wallet returned an error: {error.message}")
        case WalletResponseError():
            return RunError(f"unexpected response from the wallet: {error}")
        case _:
            return RunError(str(error))
