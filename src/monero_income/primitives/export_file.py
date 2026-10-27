"""Write a CSV file atomically: a temporary file in the same directory, then a rename.

Only writes the rows it's given; formatting is the caller's job (constitution IV).
While writing, an exclusive lock on the directory means no other run is mid-write,
so any leftover temporary file is from a killed run and safe to delete (research R3).
"""

import csv
import errno
import fcntl
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path

from monero_income.primitives.errors import ExportLockUnsupportedError, ExportWriteError

# flock errors meaning the filesystem can't lock at all, as some network shares (FR-027).
_LOCK_UNSUPPORTED = frozenset({errno.ENOLCK, errno.ENOTSUP, errno.EOPNOTSUPP})


def write_export(
    directory: Path, name: str, header: Sequence[str], rows: Iterable[Sequence[str]]
) -> Path:
    """Write ``header`` and ``rows`` to ``directory/name`` and return its absolute path.

    The file is complete when it appears: the rows go to a ``0o600`` temporary file
    that is synced and then renamed over the old file. On any failure the old file
    is unchanged and the temporary file is removed. ``OSError`` becomes
    ``ExportWriteError``; anything else, including ``KeyboardInterrupt``, propagates.
    """
    directory = directory.absolute()
    path = directory / name
    try:
        directory.mkdir(parents=True, exist_ok=True)
        dir_fd = os.open(directory, os.O_RDONLY)
        try:
            _lock(dir_fd)
            for stale in directory.glob(f".{name}.*.tmp"):
                stale.unlink(missing_ok=True)
            _write_and_replace(directory, path, header, rows)
            os.fsync(dir_fd)  # makes the rename durable
        finally:
            os.close(dir_fd)  # releases the lock
    except OSError as error:
        raise ExportWriteError(error.strerror or type(error).__name__) from error
    return path


def _lock(dir_fd: int) -> None:
    try:
        fcntl.flock(dir_fd, fcntl.LOCK_EX)
    except OSError as error:
        if error.errno in _LOCK_UNSUPPORTED:
            raise ExportLockUnsupportedError() from error
        raise


def _write_and_replace(
    directory: Path, path: Path, header: Sequence[str], rows: Iterable[Sequence[str]]
) -> None:
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
