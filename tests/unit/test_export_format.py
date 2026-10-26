import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

import pytest

from monero_income.orchestration.export_format import (
    HEADER,
    export_rows,
    format_price,
    format_timestamp,
    format_usd_value,
    format_xmr,
)
from monero_income.primitives.models import ExportRecord

TXID_A = "a" * 64
TXID_B = "b" * 64
TXID_C = "c" * 64


def ts(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp())


def record(
    txid: str = TXID_A,
    height: int = 3_530_000,
    amount: int = 1_000_000_000_000,
    occurred_at: int = ts("2026-10-17T14:03:05"),
    price: Decimal | None = Decimal("150"),
    status: Literal["provisional", "final"] | None = "final",
) -> ExportRecord:
    return ExportRecord(txid, height, amount, occurred_at, price, status)


@pytest.mark.parametrize(
    ("amount", "text"),
    [
        (1_234_567_890_123, "1.234567890123"),
        (2_000_000_000_000, "2.000000000000"),
        (1, "0.000000000001"),
        (1_234_500_000_000_000, "1234.500000000000"),
    ],
)
def test_format_xmr_has_exactly_twelve_decimals(amount: int, text: str) -> None:
    assert format_xmr(amount) == text


@pytest.mark.parametrize(
    ("moment", "text"),
    [
        ("2026-10-17T14:03:05", "2026-10-17T14:03:05Z"),
        ("2026-10-19T00:00:00", "2026-10-19T00:00:00Z"),
    ],
)
def test_format_timestamp_is_iso_8601_utc(moment: str, text: str) -> None:
    assert format_timestamp(ts(moment)) == text


@pytest.mark.parametrize(
    ("price", "text"),
    [
        (Decimal("152.3456"), "152.3456"),
        (Decimal("150"), "150"),
        (Decimal("1E+2"), "100"),
        (Decimal("163.40000000000001"), "163.40000000000001"),
        (None, "TBD"),
    ],
)
def test_format_price_keeps_full_precision_without_exponent(
    price: Decimal | None, text: str
) -> None:
    assert format_price(price) == text


@pytest.mark.parametrize(
    ("amount", "price", "text"),
    [
        (1_234_567_890_123, Decimal("152.3456"), "188.08"),
        (1_000_000_000_000, Decimal("152.345"), "152.35"),  # exactly half a cent: rounds up
        (1, Decimal("150"), "0.00"),
        (1_234_500_000_000_000, Decimal("150"), "185175.00"),
        (2_000_000_000_000, Decimal("163.40000000000001"), "326.80"),
        (1_000_000_000_000, None, "TBD"),
    ],
)
def test_format_usd_value_rounds_half_up_to_the_cent(
    amount: int, price: Decimal | None, text: str
) -> None:
    assert format_usd_value(amount, price) == text


def test_format_usd_value_beyond_the_default_context_precision() -> None:
    # 12-digit amount x 30-digit price: the product has more than 28 significant digits.
    price = Decimal("123456789012345678901234567.891")

    assert format_usd_value(999_999_999_999, price) == "123456789012222222112222222.21"


def test_export_rows_sorts_by_timestamp_then_height_then_txid() -> None:
    early = ts("2026-10-18T09:12:44")
    records = [
        record(txid=TXID_C, height=3_530_700, occurred_at=early),
        record(txid=TXID_B, height=3_530_700, occurred_at=early),  # same second and height
        record(txid=TXID_A, height=3_530_699, occurred_at=early),  # same second, lower height
        record(txid="d" * 64, height=3_532_200, occurred_at=ts("2026-10-20T12:00:00")),
        record(txid="e" * 64, height=3_532_100, occurred_at=ts("2026-10-20T18:45:10")),
        record(txid="f" * 64, height=3_000_000, occurred_at=ts("2026-10-17T14:03:05")),
    ]

    rows = export_rows(records)

    assert [(row[0][0], row[1]) for row in rows] == [
        ("f", "3000000"),
        ("a", "3530699"),
        ("b", "3530700"),
        ("c", "3530700"),
        ("d", "3532200"),  # later block, earlier timestamp: first
        ("e", "3532100"),
    ]


def test_export_rows_are_seven_columns_in_header_order() -> None:
    priced = record(amount=1_234_567_890_123, price=Decimal("152.3456"), status="provisional")

    assert export_rows([priced]) == [
        (
            TXID_A,
            "3530000",
            "2026-10-17T14:03:05Z",
            "1.234567890123",
            "152.3456",
            "provisional",
            "188.08",
        )
    ]
    assert len(HEADER) == 7
    assert HEADER == (
        "txid",
        "height",
        "timestamp_utc",
        "xmr",
        "usd_price",
        "price_status",
        "usd_value",
    )


def test_unpriced_record_shows_tbd_in_the_last_three_columns() -> None:
    (row,) = export_rows([record(amount=731_000_000_000, price=None, status=None)])

    assert row[3:] == ("0.731000000000", "TBD", "TBD", "TBD")


def test_no_value_has_an_exponent_or_a_separator() -> None:
    records = [
        record(amount=1, price=Decimal("1E+2")),
        record(amount=1_234_500_000_000_000, price=Decimal("150")),
        record(amount=2_000_000_000_000, price=Decimal("163.40000000000001")),
        record(amount=999_999_999_999, price=Decimal("123456789012345678901234567.891")),
        record(amount=10**18, price=Decimal("0.0000001")),
        record(amount=1, price=None, status=None),
    ]

    for row in export_rows(records):
        assert all("," not in value for value in row)
        assert all(not re.search("[eE]", value) for value in row[1:])
