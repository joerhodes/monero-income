from typing import Any

import pytest

from monero_income.primitives.errors import WalletResponseError
from monero_income.primitives.models import IncomingEntry
from monero_income.primitives.wallet_entries import parse_incoming


def raw_entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "txid": "ab" * 32,
        "height": 3_000_000,
        "amount": 123456789012,
        "timestamp": 1_700_000_000,
        "type": "in",
        "subaddr_index": {"major": 0, "minor": 1},
    }
    entry.update(overrides)
    return entry


def test_valid_entries_are_mapped() -> None:
    assert parse_incoming([raw_entry(), raw_entry(txid="cd" * 32, height=7)]) == [
        IncomingEntry(
            txid="ab" * 32, height=3_000_000, amount_piconero=123456789012, timestamp=1_700_000_000
        ),
        IncomingEntry(
            txid="cd" * 32, height=7, amount_piconero=123456789012, timestamp=1_700_000_000
        ),
    ]


def test_absent_in_list_is_empty() -> None:
    assert parse_incoming(None) == []


def test_uppercase_txid_is_normalized() -> None:
    assert parse_incoming([raw_entry(txid="AB" * 32)])[0].txid == "ab" * 32


@pytest.mark.parametrize(
    "raw",
    [
        {"in": []},  # not a list
        [["not", "an", "object"]],
        [{k: v for k, v in raw_entry().items() if k != "amount"}],  # missing field
        [raw_entry(amount=1.0)],  # JSON float where an int is expected
        [raw_entry(height=True)],  # bool is not an int here
        [raw_entry(timestamp="1700000000")],
        [raw_entry(amount=-1)],
        [raw_entry(height=-5)],
        [raw_entry(height=0)],
        [raw_entry(txid="ab" * 31)],  # 62 characters
        [raw_entry(txid="zz" * 32)],  # not hex
        [raw_entry(txid=123)],
    ],
)
def test_malformed_entries_are_rejected(raw: object) -> None:
    with pytest.raises(WalletResponseError):
        parse_incoming(raw)
