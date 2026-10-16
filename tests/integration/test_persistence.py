"""US1-3 / FR-016: recorded transactions persist between runs of the tool."""

from pathlib import Path

from monero_income.orchestration import CliOptions, run
from monero_income.primitives.database import open_database
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry


def test_records_survive_and_missing_directory_is_created(tmp_path: Path) -> None:
    db_path = tmp_path / "does" / "not" / "exist" / "xmr.db"
    wallet = FakeWalletRpc(
        entries=[entry("a", height=100, amount=1), entry("b", height=200, amount=2)],
        height=300,
    )

    run(
        CliOptions(db_path=str(db_path)),
        ListReporter(),
        config_path=tmp_path / "absent.toml",
        wallet_factory=lambda settings: wallet,
    )

    assert db_path.is_file()
    conn = open_database(db_path)
    try:
        rows = conn.execute(
            "SELECT height, amount_piconero FROM transactions ORDER BY height"
        ).fetchall()
    finally:
        conn.close()
    assert rows == [(100, 1), (200, 2)]


def test_default_db_path_is_under_home(tmp_path: Path, isolated_home: Path) -> None:
    run(
        CliOptions(),
        ListReporter(),
        config_path=tmp_path / "absent.toml",
        wallet_factory=lambda settings: FakeWalletRpc(height=10),
    )

    assert (isolated_home / ".local/share/monero-income/xmr.db").is_file()
