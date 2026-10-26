"""US2: a failed or interrupted export write fails the run and keeps everything else."""

import importlib
import re
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, RunResult, run
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry
from tests.integration.helpers import table

export_module = importlib.import_module("monero_income.orchestration.export")

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def at(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, 12, tzinfo=UTC).timestamp())


def wallet(count: int) -> FakeWalletRpc:
    return FakeWalletRpc(
        entries=[
            entry(str(i), height=100 + i, amount=1_000_000_000_000, timestamp=at(date(2026, 10, 1)))
            for i in range(count)
        ],
        height=1_000,
    )


def export_run(db_path: Path, fake: FakeWalletRpc, reports_path: Path | None = None) -> RunResult:
    clock = FakeClock(NOW)
    return run(
        CliOptions(
            db_path=str(db_path),
            reports_path=str(reports_path) if reports_path is not None else None,
        ),
        ListReporter(),
        config_path=db_path.parent / "absent.toml",
        wallet_factory=lambda settings: fake,
        price_source_factory=lambda settings: FakePriceSource(),
        clock=clock,
        sleep=RecordingSleep(clock),
    )


def test_unwritable_reports_path_fails_the_run_and_keeps_the_transactions(
    tmp_path: Path, isolated_home: Path
) -> None:
    db_path = tmp_path / "xmr.db"
    first = export_run(db_path, wallet(1))
    assert first.exported is not None
    previous = first.exported.path.read_bytes()
    not_a_directory = tmp_path / "file"
    not_a_directory.write_text("a file")

    with pytest.raises(RunError) as excinfo:
        export_run(db_path, wallet(2), reports_path=not_a_directory)

    target = re.escape(f"{not_a_directory / 'xmr_income.csv'}")
    assert re.fullmatch(
        f"cannot write export {target}: [^.]+\\. Recorded transactions and prices were kept;"
        " the previous export was not changed\\.",
        str(excinfo.value),
    )
    assert len(table(db_path)) == 2  # the second run's transaction was recorded (FR-008)
    assert first.exported.path.read_bytes() == previous


def test_interrupt_during_the_write_keeps_the_previous_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "xmr.db"
    first = export_run(db_path, wallet(1))
    assert first.exported is not None
    previous = first.exported.path.read_bytes()

    def interrupted(
        directory: Path, name: str, header: Sequence[str], rows: Iterable[Sequence[str]]
    ) -> Path:
        raise KeyboardInterrupt

    monkeypatch.setattr(export_module, "write_export", interrupted)

    with pytest.raises(KeyboardInterrupt):
        export_run(db_path, wallet(2))

    assert first.exported.path.read_bytes() == previous
    assert len(table(db_path)) == 2
