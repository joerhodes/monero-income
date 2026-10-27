"""write_export: a complete, owner-only CSV file replaced in one step, or nothing."""

import errno
import fcntl
import os
import stat
import threading
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from monero_income.primitives.errors import ExportLockUnsupportedError, ExportWriteError
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


# --- US2: never a broken export --------------------------------------------------------------

OLD = b"txid,height,value\nprevious export,1,2\n"
LOCK_MESSAGE = (
    "the filesystem doesn't support file locking (some network shares don't);"
    " write the export to a local directory and copy it"
)


def temporaries(directory: Path) -> list[Path]:
    return sorted(directory.glob(f".{NAME}.*.tmp"))


def failing_rows(error: BaseException) -> Iterator[Sequence[str]]:
    yield ROWS[0]
    yield ROWS[1]
    raise error


@pytest.fixture
def old_export(tmp_path: Path) -> Path:
    path = tmp_path / NAME
    path.write_bytes(OLD)
    return path


def test_failure_mid_write_keeps_the_previous_export(tmp_path: Path, old_export: Path) -> None:
    error = OSError(errno.ENOSPC, "No space left on device")

    with pytest.raises(ExportWriteError, match="No space left on device"):
        write_export(tmp_path, NAME, HEADER, failing_rows(error))

    assert old_export.read_bytes() == OLD
    assert temporaries(tmp_path) == []


def test_interrupt_mid_write_propagates_and_keeps_the_previous_export(
    tmp_path: Path, old_export: Path
) -> None:
    with pytest.raises(KeyboardInterrupt):
        write_export(tmp_path, NAME, HEADER, failing_rows(KeyboardInterrupt()))

    assert old_export.read_bytes() == OLD
    assert temporaries(tmp_path) == []


@pytest.mark.parametrize(
    ("error", "raised"),
    [
        (OSError(errno.ENOSPC, "No space left on device"), ExportWriteError),
        (KeyboardInterrupt(), KeyboardInterrupt),
    ],
)
def test_failure_without_a_previous_export_leaves_no_file(
    tmp_path: Path, error: BaseException, raised: type[BaseException]
) -> None:
    directory = tmp_path / "reports"

    with pytest.raises(raised):
        write_export(directory, NAME, HEADER, failing_rows(error))

    assert list(directory.iterdir()) == []


def test_stale_temporary_files_are_removed_and_other_files_kept(tmp_path: Path) -> None:
    directory = tmp_path / "reports"
    directory.mkdir()
    (directory / f".{NAME}.abc123.tmp").write_bytes(b"junk from a killed run")
    (directory / "notes.txt").write_text("mine")

    write_export(directory, NAME, HEADER, ROWS)

    assert sorted(p.name for p in directory.iterdir()) == ["notes.txt", NAME]


def test_export_is_owner_only_even_when_the_previous_one_was_not(
    tmp_path: Path, old_export: Path
) -> None:
    old_export.chmod(0o644)
    seen: list[int] = []

    def watching_rows() -> Iterator[Sequence[str]]:
        seen.extend(stat.S_IMODE(p.stat().st_mode) for p in temporaries(tmp_path))
        yield from ROWS

    path = write_export(tmp_path, NAME, HEADER, watching_rows())

    assert seen == [0o600]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_a_held_lock_makes_the_write_wait(tmp_path: Path) -> None:
    done = threading.Event()
    errors: list[BaseException] = []

    def write() -> None:
        try:
            write_export(tmp_path, NAME, HEADER, ROWS)
        except BaseException as error:  # reported by the assertions below
            errors.append(error)
        finally:
            done.set()

    dir_fd = os.open(tmp_path, os.O_RDONLY)
    try:
        fcntl.flock(dir_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        writer = threading.Thread(target=write)
        writer.start()
        assert not done.wait(timeout=0.2)  # blocked on the lock
        assert not (tmp_path / NAME).exists()
    finally:
        os.close(dir_fd)  # releases the lock

    writer.join(timeout=5)
    assert done.is_set()
    assert errors == []
    assert (tmp_path / NAME).is_file()


def test_reports_path_that_is_a_file_fails(tmp_path: Path) -> None:
    not_a_directory = tmp_path / "reports"
    not_a_directory.write_text("a file")

    with pytest.raises(ExportWriteError, match=r"Not a directory|File exists"):
        write_export(not_a_directory, NAME, HEADER, ROWS)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores directory permissions")
def test_read_only_directory_fails(tmp_path: Path) -> None:
    directory = tmp_path / "reports"
    directory.mkdir(mode=0o500)
    try:
        with pytest.raises(ExportWriteError, match="Permission denied"):
            write_export(directory, NAME, HEADER, ROWS)
    finally:
        directory.chmod(0o700)


@pytest.mark.parametrize("code", [errno.ENOLCK, errno.ENOTSUP, errno.EOPNOTSUPP])
def test_filesystem_without_locking_fails_with_advice(
    tmp_path: Path, old_export: Path, monkeypatch: pytest.MonkeyPatch, code: int
) -> None:
    def no_locking(fd: int, operation: int) -> None:
        raise OSError(code, os.strerror(code))

    monkeypatch.setattr("monero_income.primitives.export_file.fcntl.flock", no_locking)

    with pytest.raises(ExportLockUnsupportedError) as excinfo:
        write_export(tmp_path, NAME, HEADER, ROWS)

    assert str(excinfo.value) == LOCK_MESSAGE
    assert old_export.read_bytes() == OLD
    assert temporaries(tmp_path) == []


def test_other_lock_errors_are_plain_write_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def bad_descriptor(fd: int, operation: int) -> None:
        raise OSError(errno.EBADF, os.strerror(errno.EBADF))

    monkeypatch.setattr("monero_income.primitives.export_file.fcntl.flock", bad_descriptor)

    with pytest.raises(ExportWriteError) as excinfo:
        write_export(tmp_path, NAME, HEADER, ROWS)

    assert type(excinfo.value) is ExportWriteError
    assert str(excinfo.value) == os.strerror(errno.EBADF)
