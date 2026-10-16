"""US2: later runs add only what's new and never touch what's recorded."""

from pathlib import Path

from tests.fakes.wallet import FakeWalletRpc, entry
from tests.integration.helpers import run_once, table


def test_second_run_with_no_changes_records_nothing_and_changes_nothing(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    wallet = FakeWalletRpc(
        entries=[entry("a", height=900, amount=1), entry("b", height=12_000, amount=2)],
        height=15_000,
    )
    assert run_once(db_path, wallet).recorded == 2
    before = table(db_path)

    assert run_once(db_path, wallet).recorded == 0
    assert table(db_path) == before


def test_only_the_new_entry_is_added(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    wallet = FakeWalletRpc(entries=[entry("a", height=900, amount=1)], height=1_000)
    run_once(db_path, wallet)
    before = table(db_path)

    new = entry("new", height=1_500, amount=42)
    wallet.entries.append(new)
    wallet.height = 2_000

    assert run_once(db_path, wallet).recorded == 1
    after = table(db_path)
    assert set(after) - set(before) == {(new["txid"], 1_500, 42, new["timestamp"], "2023-11-14")}
    assert set(before) <= set(after)


def test_reorged_entry_inside_the_overlap_is_not_duplicated_or_changed(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    moved = entry("moved", height=5_000, amount=7)
    wallet = FakeWalletRpc(entries=[moved], height=5_010)
    run_once(db_path, wallet)
    before = table(db_path)

    moved["height"] = 4_970  # re-mined 30 blocks lower after a reorg

    assert run_once(db_path, wallet).recorded == 0
    assert table(db_path) == before


def test_second_run_resumes_61_blocks_below_the_last_recorded_height(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    wallet = FakeWalletRpc(entries=[entry("a", height=1_000, amount=1)], height=25_000)
    run_once(db_path, wallet)
    wallet.calls.clear()

    run_once(db_path, wallet)

    assert wallet.calls[0] == (939, 10_939)
    assert wallet.calls[-1][1] == 25_000


def test_empty_wallet_records_nothing(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"

    assert run_once(db_path, FakeWalletRpc(height=30_000)).recorded == 0
    assert table(db_path) == []
