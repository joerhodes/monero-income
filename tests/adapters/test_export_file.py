"""write_export: a complete CSV file replaced in one step."""

from pathlib import Path

import pytest

from monero_income.primitives.export_file import write_export

NAME = "xmr_income.csv"
HEADER = ("txid", "height", "value")
ROWS = [("a" * 64, "100", "1.50"), ("b" * 64, "101", "TBD")]


def test_writes_lf_terminated_unquoted_csv(tmp_path: Path) -> None:
    path = write_export(tmp_path, NAME, HEADER, ROWS)

    assert path.read_bytes() == (
        b"txid,height,value\n" + b"a" * 64 + b",100,1.50\n" + b"b" * 64 + b",101,TBD\n"
    )


def test_returns_the_absolute_final_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    path = write_export(Path("reports"), NAME, HEADER, ROWS)

    assert path == tmp_path / "reports" / NAME
    assert path.is_absolute()


def test_creates_a_missing_directory_with_parents(tmp_path: Path) -> None:
    directory = tmp_path / "a" / "b" / "c"

    path = write_export(directory, NAME, HEADER, ROWS)

    assert path == directory / NAME
    assert path.is_file()


def test_second_write_replaces_the_first_in_full(tmp_path: Path) -> None:
    write_export(tmp_path, NAME, HEADER, ROWS)

    path = write_export(tmp_path, NAME, HEADER, ROWS[:1])

    assert path.read_text() == "txid,height,value\n" + "a" * 64 + ",100,1.50\n"


def test_no_rows_writes_the_header_only(tmp_path: Path) -> None:
    path = write_export(tmp_path, NAME, HEADER, [])

    assert path.read_bytes() == b"txid,height,value\n"
