"""run(): the entry point for one full run of the tool. Testable without Typer."""

import sqlite3
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from monero_income.orchestration.errors import RunError
from monero_income.orchestration.export import (
    EXPORT_FILE_NAME,
    ExportSummary,
    read_export_rows,
    write_export_file,
)
from monero_income.orchestration.price_import import ImportSummary, import_prices
from monero_income.orchestration.pricing import PricingSummary, price_days
from monero_income.orchestration.settings import (
    CliOptions,
    Settings,
    default_config_path,
    resolve_settings,
)
from monero_income.orchestration.summary import (
    IncomeSummaries,
    SummaryDataError,
    build_summaries,
    summary_failure_message,
)
from monero_income.orchestration.sync import sync
from monero_income.orchestration.valuation import default_delay
from monero_income.primitives.config_file import read_config
from monero_income.primitives.database import open_database
from monero_income.primitives.errors import (
    ConfigFileError,
    ExportWriteError,
    ImportFileError,
    SchemaTooNewError,
    StorageError,
    StorageReadError,
    StorageWriteError,
    UnknownTimeZoneError,
    WalletError,
    WalletLoginError,
    WalletResponseError,
    WalletRpcError,
    WalletUnreachableError,
)
from monero_income.primitives.export_db import export_records
from monero_income.primitives.models import ExportRecord
from monero_income.primitives.price_source import CoinGeckoPriceSource, PriceSource
from monero_income.primitives.timezones import load_zone
from monero_income.primitives.wallet_rpc import HttpWalletRpc, WalletRpc

# Resolved at call time, so tests can replace them (contracts/run-api.md).
_sleep = time.sleep


class Reporter(Protocol):
    def warning(self, message: str) -> None: ...


@dataclass(frozen=True)
class RunResult:
    recorded: int
    imported: ImportSummary | None = None  # None when --import-prices wasn't given
    pricing: PricingSummary = field(default_factory=PricingSummary)
    exported: ExportSummary | None = None  # set by every successful run()
    summaries: IncomeSummaries | None = None  # set by every successful run()


class SummaryError(RunError):
    """The summary step failed after the export was written (FR-018)."""

    def __init__(self, message: str, result: RunResult) -> None:
        super().__init__(message)
        self.result = result


def make_wallet(settings: Settings) -> WalletRpc:
    return HttpWalletRpc(settings.rpc_url, settings.username, settings.password)


def make_price_source(settings: Settings) -> PriceSource:
    return CoinGeckoPriceSource(
        settings.coingecko_url, settings.coin_id, settings.api_key, settings.api_key_type
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def run(
    options: CliOptions,
    reporter: Reporter,
    *,
    config_path: Path | None = None,
    wallet_factory: Callable[[Settings], WalletRpc] = make_wallet,
    price_source_factory: Callable[[Settings], PriceSource] | None = None,
    connect: Callable[[Path], sqlite3.Connection] = open_database,
    clock: Callable[[], datetime] | None = None,
    sleep: Callable[[float], None] | None = None,
    summary_reader: Callable[[sqlite3.Connection], Sequence[ExportRecord]] = export_records,
) -> RunResult:
    """Run once: resolve settings, open the database, sync, import (if asked), price, export,
    then build the income summaries.

    ``config_path`` defaults to ``~/.config/monero-income/config.toml``, expanded
    at call time; so are the price source, clock, and sleep defaults. Every
    expected failure is raised as ``RunError``; price-source problems don't fail
    the run; ``KeyboardInterrupt`` propagates. A failure in the summary step comes after the
    export is written and is raised as ``SummaryError`` (FR-018).
    """
    make_source = price_source_factory or make_price_source
    now = clock or utc_now
    wait = sleep or _sleep
    path = config_path if config_path is not None else default_config_path()
    try:
        raw = read_config(path)
    except ConfigFileError as error:
        raise RunError(f"cannot read config file {error}") from error
    settings, warnings = resolve_settings(options, raw, path)
    for warning in warnings:
        reporter.warning(warning)
    # Checked before anything is opened or synced (FR-006); None is the machine's local zone.
    zone: ZoneInfo | None = None
    if settings.timezone is not None:
        try:
            zone = load_zone(settings.timezone)
        except UnknownTimeZoneError as error:
            raise RunError(f"invalid timezone: unknown time zone '{settings.timezone}'") from error
    today = now().astimezone(zone).date()

    try:
        conn = connect(settings.db_path)
        try:
            wallet = wallet_factory(settings)
            try:
                recorded = sync(conn, wallet)
            finally:
                _close(wallet)
            imported = None
            if settings.import_prices is not None:
                try:
                    imported = import_prices(
                        conn, settings.import_prices, today=now().date(), clock=now
                    )
                except ImportFileError as error:
                    raise RunError(
                        f"cannot import prices from {settings.import_prices}: {error}"
                    ) from error
            source = make_source(settings)
            try:
                pricing = price_days(
                    conn,
                    source,
                    today=now().date(),
                    clock=now,
                    sleep=wait,
                    delay=settings.min_request_delay or default_delay(settings.api_key is not None),
                )
            finally:
                _close(source)
            rows = read_export_rows(conn)
            # Same connection and no commit in between, so both reads see one snapshot
            # (research R1). A failure here waits until the export is written (FR-018).
            summary_records: Sequence[ExportRecord] = ()
            summary_failure: Exception | None = None
            try:
                summary_records = summary_reader(conn)
            except Exception as error:  # deliberate: the summary step is guarded
                summary_failure = error
        finally:
            conn.close()
        # Written only once every earlier step succeeded (FR-002).
        try:
            exported = write_export_file(settings.reports_path, rows)
        except ExportWriteError as error:
            target = settings.reports_path.absolute() / EXPORT_FILE_NAME
            raise RunError(
                f"cannot write export {target}: {error}. Recorded transactions and prices"
                " were kept; the previous export was not changed."
            ) from error
    except (StorageError, WalletError) as error:
        raise _run_error(error, settings) from error
    partial = RunResult(recorded=recorded, imported=imported, pricing=pricing, exported=exported)
    try:
        if summary_failure is not None:
            raise summary_failure
        summaries = build_summaries(summary_records, today, zone)
    except Exception as error:  # deliberate: any failure is one clean error (research R10)
        message = summary_failure_message(_summary_reason(error, settings), exported.path)
        raise SummaryError(message, partial) from error
    return RunResult(
        recorded=recorded,
        imported=imported,
        pricing=pricing,
        exported=exported,
        summaries=summaries,
    )


def _summary_reason(error: Exception, settings: Settings) -> str:
    """The reason part of the FR-018 message (research R10)."""
    match error:
        case StorageReadError():
            return f"cannot read database {settings.db_path}: {error}"
        case SummaryDataError():
            return str(error)
        case _:
            return f"unexpected {type(error).__name__}: {error}"


def _close(resource: object) -> None:
    close = getattr(resource, "close", None)
    if callable(close):
        close()


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
