from decimal import Decimal

import pytest

from monero_income.primitives.price_parse import NoPrice, Price, parse_history_price


def body(usd: object) -> dict[str, object]:
    return {"id": "monero", "market_data": {"current_price": {"usd": usd, "eur": Decimal(1)}}}


def test_decimal_price_is_kept_exactly() -> None:
    assert parse_history_price(body(Decimal("152.3456"))) == Price(Decimal("152.3456"))


def test_integer_price_becomes_decimal() -> None:
    result = parse_history_price(body(152))

    assert result == Price(Decimal(152))
    assert isinstance(result, Price)
    assert isinstance(result.usd_price, Decimal)


@pytest.mark.parametrize(
    "response",
    [
        {"id": "monero"},  # no market_data: the day isn't published yet
        {"market_data": {}},
        {"market_data": {"current_price": {"eur": Decimal(1)}}},
        {"market_data": None},
        [],
        None,
    ],
)
def test_missing_price_is_no_price(response: object) -> None:
    result = parse_history_price(response)

    assert isinstance(result, NoPrice)
    assert result.reason == "no price for this date"


@pytest.mark.parametrize(
    "usd",
    [True, 0, Decimal(0), -1, Decimal("-0.5"), "152.3", Decimal("NaN"), Decimal("Infinity"), 1.5],
)
def test_invalid_price_is_no_price(usd: object) -> None:
    assert parse_history_price(body(usd)) == NoPrice("invalid price")
