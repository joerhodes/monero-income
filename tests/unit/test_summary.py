"""Aggregation of recorded transactions into the income summaries (feature 004)."""

from collections.abc import Callable
from datetime import UTC, date, datetime


def test_local_tz_fixture_sets_the_local_zone(local_tz: Callable[[str], None]) -> None:
    local_tz("America/New_York")
    assert datetime(2026, 11, 1, 3, 30, tzinfo=UTC).astimezone(None).date() == date(2026, 10, 31)
