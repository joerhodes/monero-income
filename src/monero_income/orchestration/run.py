"""run(): the entry point for one full run of the tool. Testable without Typer."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from monero_income.orchestration.settings import (
    CliOptions,
    Settings,
    default_config_path,
    resolve_settings,
)
from monero_income.orchestration.sync import sync
from monero_income.primitives.config_file import read_config
from monero_income.primitives.database import open_database
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
    at call time.
    """
    path = config_path if config_path is not None else default_config_path()
    settings, warnings = resolve_settings(options, read_config(path), path)
    for warning in warnings:
        reporter.warning(warning)

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
    return SyncResult(recorded=recorded)
