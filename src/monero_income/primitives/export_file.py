"""Write a CSV file atomically: a temporary file in the same directory, then a rename.

Only writes the rows it's given; formatting is the caller's job (constitution IV).
"""

import csv
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path


def write_export(
    directory: Path, name: str, header: Sequence[str], rows: Iterable[Sequence[str]]
) -> Path:
    """Write ``header`` and ``rows`` to ``directory/name`` and return its absolute path.

    The file is complete when it appears: the rows go to a ``0o600`` temporary file
    that is synced and then renamed over the old file.
    """
    directory = directory.absolute()
    directory.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=f".{name}.", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
        file.flush()
        os.fsync(file.fileno())
    path = directory / name
    os.replace(tmp, path)
    return path
