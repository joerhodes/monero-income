from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from monero_income.orchestration.valuation import (
    default_delay,
    history_cutoff,
    plan_lookups,
    price_status,
    settled_at,
    usd_value,
)
from monero_income.primitives.models import PriceNeed

TODAY = date(2026, 10, 17)


def test_history_cutoff_is_364_days_back() -> None:
    assert history_cutoff(TODAY) == date(2025, 10, 18)


def test_plan_lookups_splits_requestable_oldest_first_from_too_old() -> None:
    needs = [
        PriceNeed(date(2026, 10, 16), has_provisional=True),
        PriceNeed(date(2025, 10, 17), has_provisional=False),  # 365 days old
        PriceNeed(date(2025, 10, 18), has_provisional=False),  # 364 days old
        PriceNeed(date(2025, 1, 1), has_provisional=True),  # provisional, aged out
        PriceNeed(date(2026, 3, 1), has_provisional=False),
    ]

    plan = plan_lookups(needs, TODAY)

    assert [need.date_utc for need in plan.requestable] == [
        date(2025, 10, 18),
        date(2026, 3, 1),
        date(2026, 10, 16),
    ]
    assert [need.date_utc for need in plan.too_old] == [date(2025, 1, 1), date(2025, 10, 17)]


def test_settled_one_hour_after_the_utc_day_ends() -> None:
    assert settled_at(date(2026, 10, 16)) == datetime(2026, 10, 17, 1, 0, tzinfo=UTC)


def test_price_status_changes_at_settled_at() -> None:
    day = date(2026, 10, 16)

    assert price_status(day, settled_at(day) - timedelta(seconds=1)) == "provisional"
    assert price_status(day, settled_at(day)) == "final"
    assert price_status(day, datetime(2026, 10, 16, 12, tzinfo=UTC)) == "provisional"


def test_default_delay_depends_on_a_key() -> None:
    assert default_delay(True) == Decimal("2.5")
    assert default_delay(False) == Decimal("6.0")


def test_usd_value_is_exact() -> None:
    assert usd_value(1_234_567_890_123, Decimal("152.3456")) == Decimal("188.0809859615225088")


def test_usd_value_stays_exact_beyond_the_default_28_digit_context() -> None:
    amount = 12_345_678_901_234_567_890  # 20 digits of piconero
    price = Decimal("123.456789012345678901234567891")  # 30 significant digits

    value = usd_value(amount, price)

    # Exactly amount * price / 10**12, which needs 50 significant digits.
    assert value == Decimal("1524157875.32388367503429357751425087877625361999")
