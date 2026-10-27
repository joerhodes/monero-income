"""US3: the export goes to --reports-path, else reports_path in the config file, else ~/reports."""

import errno
import os
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, RunResult, run
from tests.fakes.clock import FakeClock, RecordingSleep
from tests.fakes.price_source import FakePriceSource
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

NAME = "xmr_income.csv"


def config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(body)
    path.chmod(0o600)
    return path


def export_run(
    tmp_path: Path,
    *,
    reports_path: str | None = None,
    config_path: Path | None = None,
    wallet: FakeWalletRpc | None = None,
) -> RunResult:
    clock = FakeClock()
    fake = wallet or FakeWalletRpc(entries=[entry("a", height=100, amount=1)], height=200)
    return run(
        CliOptions(db_path=str(tmp_path / "xmr.db"), reports_path=reports_path),
        ListReporter(),
        config_path=config_path or tmp_path / "absent.toml",
        wallet_factory=lambda settings: fake,
        price_source_factory=lambda settings: FakePriceSource(),
        clock=clock,
        sleep=RecordingSleep(clock),
    )


def exported_path(result: RunResult) -> Path:
    assert result.exported is not None
    assert result.exported.path.is_file()
    return result.exported.path


def test_default_is_reports_in_home(tmp_path: Path, isolated_home: Path) -> None:
    assert exported_path(export_run(tmp_path)) == isolated_home / "reports" / NAME


def test_config_key_chooses_the_directory(tmp_path: Path) -> None:
    cfg = config(tmp_path, f'reports_path = "{tmp_path / "cfg-reports"}"\n')

    result = export_run(tmp_path, config_path=cfg)

    assert exported_path(result) == tmp_path / "cfg-reports" / NAME


def test_option_overrides_the_config_key(tmp_path: Path) -> None:
    cfg = config(tmp_path, f'reports_path = "{tmp_path / "cfg-reports"}"\n')

    result = export_run(tmp_path, config_path=cfg, reports_path=str(tmp_path / "opt-reports"))

    assert exported_path(result) == tmp_path / "opt-reports" / NAME
    assert not (tmp_path / "cfg-reports").exists()


def test_missing_nested_directory_is_created(tmp_path: Path) -> None:
    result = export_run(tmp_path, reports_path=str(tmp_path / "a" / "b" / "c"))

    assert exported_path(result) == tmp_path / "a" / "b" / "c" / NAME


def test_home_is_expanded(tmp_path: Path, isolated_home: Path) -> None:
    cfg = config(tmp_path, 'reports_path = "~/elsewhere"\n')

    assert (
        exported_path(export_run(tmp_path, config_path=cfg)) == isolated_home / "elsewhere" / NAME
    )


def test_relative_path_resolves_against_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    path = exported_path(export_run(tmp_path, reports_path="rel"))

    assert path == tmp_path / "rel" / NAME
    assert path.is_absolute()


@pytest.mark.parametrize(
    ("body", "option", "message"),
    [
        ("reports_path = 5\n", None, "invalid reports_path in {config}: expected a string"),
        ('reports_path = ""\n', None, "invalid reports_path: must not be empty"),
        ("", "", "invalid reports_path: must not be empty"),
    ],
)
def test_invalid_setting_fails_before_the_wallet_is_contacted(
    tmp_path: Path, isolated_home: Path, body: str, option: str | None, message: str
) -> None:
    cfg = config(tmp_path, body)
    wallet = FakeWalletRpc(entries=[entry("a", height=100, amount=1)], height=200)

    with pytest.raises(RunError) as excinfo:
        export_run(tmp_path, reports_path=option, config_path=cfg, wallet=wallet)

    assert str(excinfo.value) == message.format(config=cfg)
    assert wallet.calls == []
    assert not (isolated_home / "reports").exists()


def test_filesystem_without_locking_fails_with_advice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_locking(fd: int, operation: int) -> None:
        raise OSError(errno.ENOLCK, os.strerror(errno.ENOLCK))

    monkeypatch.setattr("monero_income.primitives.export_file.fcntl.flock", no_locking)
    target = tmp_path / "share" / NAME

    with pytest.raises(RunError) as excinfo:
        export_run(tmp_path, reports_path=str(tmp_path / "share"))

    assert str(excinfo.value) == (
        f"cannot write export {target}: the filesystem doesn't support file locking"
        " (some network shares don't); write the export to a local directory and copy it."
        " Recorded transactions and prices were kept; the previous export was not changed."
    )
    assert list(target.parent.iterdir()) == []  # no export, and no temporary file
