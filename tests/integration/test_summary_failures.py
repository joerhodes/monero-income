"""FR-018: a failure while reading or computing the summaries is one clean error, after the export.

The reader is injected (research R10): a real database can't produce these failures once the
export's own read has succeeded, so each test simulates one through ``summary_reader``.
"""

import sqlite3
from collections.abc import Callable, Sequence
from decimal import Decimal
from pathlib import Path

import pytest

from monero_income.orchestration import SummaryError
from monero_income.primitives.errors import StorageReadError
from monero_income.primitives.export_db import export_records
from monero_income.primitives.models import ExportRecord
from tests.integration.helpers import table
from tests.integration.test_summaries import prices_rows, summary_run, wallet

Reader = Callable[[sqlite3.Connection], Sequence[ExportRecord]]
GOOD = ExportRecord("good-tx", 1, 10**12, 1_790_000_000, Decimal(150), "final")


def raising(error: BaseException) -> Reader:
    def reader(conn: sqlite3.Connection) -> Sequence[ExportRecord]:
        raise error

    return reader


def returning(*found: ExportRecord) -> Reader:
    def reader(conn: sqlite3.Connection) -> Sequence[ExportRecord]:
        return [GOOD, *found]

    return reader


@pytest.mark.parametrize(
    ("make_reader", "reason"),
    [
        pytest.param(
            lambda: raising(StorageReadError("invalid stored price 'abc'")),
            "cannot read database {db}: invalid stored price 'abc'",
            id="read: storage error",
        ),
        pytest.param(
            lambda: raising(RuntimeError("boom")),
            "unexpected RuntimeError: boom",
            id="read: anything else",
        ),
        pytest.param(
            lambda: returning(
                ExportRecord("nan-tx", 2, 10**12, 1_790_000_000, Decimal("NaN"), "final")
            ),
            "unexpected data for transaction nan-tx: invalid price",
            id="compute: NaN price",
        ),
        pytest.param(
            lambda: returning(ExportRecord("neg-tx", 2, -1, 1_790_000_000, None, None)),
            "unexpected data for transaction neg-tx: invalid amount",
            id="compute: negative amount",
        ),
        pytest.param(
            lambda: returning(ExportRecord("status-tx", 2, 10**12, 1_790_000_000, None, "final")),
            "unexpected data for transaction status-tx: invalid price status",
            id="compute: status without a price",
        ),
    ],
)
def test_a_summary_failure_keeps_the_export(
    tmp_path: Path, make_reader: Callable[[], Reader], reason: str
) -> None:
    reference_db = tmp_path / "reference" / "xmr.db"
    reference_db.parent.mkdir()
    reference = summary_run(reference_db, wallet())
    assert reference.exported is not None
    reference_bytes = reference.exported.path.read_bytes()
    db_path = tmp_path / "xmr.db"

    with pytest.raises(SummaryError) as raised:
        summary_run(db_path, wallet(), summary_reader=make_reader())

    error = raised.value
    exported = error.result.exported
    assert exported is not None
    assert error.result.summaries is None
    assert str(error).startswith("cannot show the income summaries: ")
    assert reason.format(db=db_path) in str(error)
    assert str(error).endswith(
        f"The export was written to {exported.path}; recorded transactions and prices were kept."
    )
    assert exported.path.is_absolute()
    # The export on disk is what this run wrote, and it matches a run whose summaries worked.
    assert exported.path.read_bytes() == reference_bytes
    assert table(db_path) == table(reference_db)
    assert prices_rows(db_path) == prices_rows(reference_db)
    conn = sqlite3.connect(db_path)
    try:
        assert len(export_records(conn)) == 3
    finally:
        conn.close()


def test_an_interrupt_while_reading_is_not_turned_into_an_error(tmp_path: Path) -> None:
    with pytest.raises(KeyboardInterrupt):
        summary_run(tmp_path / "xmr.db", wallet(), summary_reader=raising(KeyboardInterrupt()))
