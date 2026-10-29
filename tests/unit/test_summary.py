"""Aggregation of recorded transactions into the income summaries (feature 004)."""

from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

import pytest

from monero_income.orchestration.summary import (
    ANNUAL_TITLE,
    MONTHLY_TITLE,
    WEEKLY_TITLE,
    PeriodFigures,
    Summary,
    SummaryDataError,
    build_summaries,
    check_record,
    exact_sum,
    local_date,
    month_labels,
    week_label,
    week_labels,
    year_labels,
)
from monero_income.primitives.models import ExportRecord

NY = ZoneInfo("America/New_York")
TODAY = date(2026, 10, 27)
XMR = 10**12


def ts(moment: str) -> int:
    return int(datetime.fromisoformat(moment).replace(tzinfo=UTC).timestamp())


def rec(
    moment: str,
    amount: int,
    price: str | None = None,
    status: Literal["provisional", "final"] | None = None,
    txid: str = "tx",
) -> ExportRecord:
    if price is not None and status is None:
        status = "final"
    usd_price = None if price is None else Decimal(price)
    return ExportRecord(txid, 1, amount, ts(moment), usd_price, status)


def row(summary: Summary, label: str) -> PeriodFigures:
    (figures,) = [p for p in summary.periods if p.label == label]
    return figures


def test_local_tz_fixture_sets_the_local_zone(local_tz: Callable[[str], None]) -> None:
    local_tz("America/New_York")
    assert datetime(2026, 11, 1, 3, 30, tzinfo=UTC).astimezone(None).date() == date(2026, 10, 31)


# Labels and ranges


def test_week_labels_are_the_26_weeks_ending_with_today() -> None:
    labels = week_labels(TODAY)
    assert len(labels) == 26
    assert labels[0] == "2026-W19"
    assert labels[-1] == "2026-W44"


def test_month_and_year_labels() -> None:
    months = month_labels(TODAY)
    assert len(months) == 12
    assert (months[0], months[-1]) == ("2025-11", "2026-10")
    assert year_labels(TODAY) == ["2023", "2024", "2025", "2026"]


def test_week_labels_across_a_year_boundary() -> None:
    assert week_labels(date(2027, 1, 20))[-4:] == ["2026-W53", "2027-W01", "2027-W02", "2027-W03"]


def test_week_label_uses_the_iso_year_and_pads_the_week() -> None:
    assert week_label(date(2027, 1, 1)) == "2026-W53"
    assert week_label(date(2026, 2, 9)) == "2026-W07"


# Local dates


def test_local_date_in_a_named_zone() -> None:
    assert local_date(ts("2026-11-01T03:30:00"), NY) == date(2026, 10, 31)
    assert local_date(ts("2026-10-26T03:30:00"), NY) == date(2026, 10, 25)


def test_local_date_in_the_machine_zone(local_tz: Callable[[str], None]) -> None:
    local_tz("UTC")
    assert local_date(ts("2026-11-01T03:30:00"), None) == date(2026, 11, 1)


# Exact sums


def test_exact_sum_keeps_every_digit() -> None:
    values = [Decimal("12345678901234567890.123456789012345"), Decimal("0.000000000000000001")]
    assert exact_sum(values) == Decimal("12345678901234567890.123456789012345001")


def test_exact_sum_of_nothing_is_zero() -> None:
    assert exact_sum([]) == Decimal(0)


# build_summaries


def test_a_month_sums_exactly_and_stays_unrounded() -> None:
    records = [
        rec("2026-05-05T12:00:00", 1_500_000_000_000, "150"),
        rec("2026-05-20T12:00:00", 250_000_000_000, "160.004"),
    ]
    may = row(build_summaries(records, TODAY, NY).monthly, "2026-05")
    assert may.piconero == 1_750_000_000_000
    assert may.usd == Decimal("265.001")


def test_an_unpriced_record_adds_xmr_only() -> None:
    records = [
        rec("2026-05-05T12:00:00", XMR, "150"),
        rec("2026-05-06T12:00:00", 731_000_000_000),
    ]
    may = row(build_summaries(records, TODAY, NY).monthly, "2026-05")
    assert may.piconero == 1_731_000_000_000
    assert may.usd == Decimal(150)


def test_empty_periods_are_zero() -> None:
    summaries = build_summaries([rec("2026-05-05T12:00:00", XMR, "150")], TODAY, NY)
    assert row(summaries.monthly, "2026-04") == PeriodFigures(
        "2026-04", 0, Decimal(0), False, False
    )


def test_a_record_older_than_the_range_counts_only_as_a_transaction() -> None:
    summaries = build_summaries([rec("2019-06-01T12:00:00", XMR, "150")], TODAY, NY)
    assert summaries.transactions == 1
    for summary in (summaries.weekly, summaries.monthly, summaries.annual):
        assert all(p.piconero == 0 for p in summary.periods)
        assert summary.total.piconero == 0


def test_a_record_after_the_current_periods_counts_in_nothing() -> None:
    # The spec's edge case: dated after the current period (2027 is after this year too).
    summaries = build_summaries([rec("2027-02-15T12:00:00", XMR, "150")], TODAY, NY)
    for summary in (summaries.weekly, summaries.monthly, summaries.annual):
        assert summary.total == PeriodFigures("Total", 0, Decimal(0), False, False)


def test_local_midnight_decides_the_period() -> None:
    late_october = build_summaries([rec("2026-11-01T03:30:00", XMR)], TODAY, NY)
    assert row(late_october.monthly, "2026-10").piconero == XMR
    sunday_night = build_summaries([rec("2026-10-26T03:30:00", XMR)], TODAY, NY)
    assert row(sunday_night.weekly, "2026-W43").piconero == XMR


def test_both_sides_of_a_daylight_saving_change() -> None:
    before, after = "2026-11-01T03:30:00", "2026-11-02T04:30:00"  # 23:30 EDT, then 23:30 EST
    assert local_date(ts(before), NY) == date(2026, 10, 31)
    assert local_date(ts(after), NY) == date(2026, 11, 1)
    summaries = build_summaries(
        [rec(before, XMR, txid="before"), rec(after, 2 * XMR, txid="after")], date(2026, 11, 10), NY
    )
    assert row(summaries.monthly, "2026-10").piconero == XMR
    assert row(summaries.monthly, "2026-11").piconero == 2 * XMR
    assert row(summaries.weekly, "2026-W44").piconero == 3 * XMR


def test_a_week_split_across_two_months() -> None:
    records = [rec("2026-08-31T12:00:00", XMR), rec("2026-09-01T12:00:00", 2 * XMR)]
    summaries = build_summaries(records, TODAY, NY)
    assert row(summaries.weekly, "2026-W36").piconero == 3 * XMR
    assert row(summaries.monthly, "2026-08").piconero == XMR
    assert row(summaries.monthly, "2026-09").piconero == 2 * XMR


def test_totals_are_the_exact_sums_of_their_periods() -> None:
    records = [
        rec("2025-03-14T09:00:00", 1_500_000_000_000, "150"),
        rec("2026-05-05T12:00:00", 250_000_000_000, "160.004"),
        rec("2026-06-10T08:30:00", 1_234_500_000_000_000, "152.345"),
        rec("2026-10-27T11:00:00", 2 * XMR, "163.40000000000001"),
    ]
    summaries = build_summaries(records, TODAY, NY)
    for summary in (summaries.weekly, summaries.monthly, summaries.annual):
        assert summary.total.piconero == sum(p.piconero for p in summary.periods)
        assert summary.total.usd == exact_sum(p.usd for p in summary.periods)
    assert summaries.annual.total.usd == Decimal("188661.70350000000002")


def test_counts_order_and_titles() -> None:
    summaries = build_summaries([], TODAY, NY)
    assert [len(s.periods) for s in (summaries.weekly, summaries.monthly, summaries.annual)] == [
        26,
        12,
        4,
    ]
    assert [s.title for s in (summaries.weekly, summaries.monthly, summaries.annual)] == [
        WEEKLY_TITLE,
        MONTHLY_TITLE,
        ANNUAL_TITLE,
    ]
    assert [p.label for p in summaries.weekly.periods] == week_labels(TODAY)
    assert [p.label for p in summaries.monthly.periods] == month_labels(TODAY)
    assert [p.label for p in summaries.annual.periods] == year_labels(TODAY)


def test_no_records_gives_zeros() -> None:
    summaries = build_summaries([], TODAY, NY)
    assert summaries.transactions == 0
    for summary in (summaries.weekly, summaries.monthly, summaries.annual):
        assert all(p.piconero == 0 and p.usd == 0 for p in (*summary.periods, summary.total))


# Marks (FR-012, US2)


def flags(figures: PeriodFigures) -> tuple[bool, bool]:
    return figures.provisional, figures.unpriced


def test_a_provisional_price_flags_its_period() -> None:
    summaries = build_summaries(
        [rec("2026-10-27T11:00:00", 2 * XMR, "163.4", "provisional")], TODAY, NY
    )
    assert flags(row(summaries.weekly, "2026-W44")) == (True, False)
    assert row(summaries.weekly, "2026-W44").usd == Decimal("326.8")


def test_an_unpriced_record_flags_its_period_and_adds_no_usd() -> None:
    records = [rec("2026-10-20T18:45:10", 731_000_000_000), rec("2026-10-21T12:00:00", XMR, "150")]
    summaries = build_summaries(records, TODAY, NY)
    week = row(summaries.weekly, "2026-W43")
    assert flags(week) == (False, True)
    assert week.usd == Decimal(150)
    assert week.piconero == 1_731_000_000_000


def test_a_period_with_both_kinds_has_both_flags() -> None:
    records = [
        rec("2026-10-27T11:00:00", 2 * XMR, "163.4", "provisional"),
        rec("2026-10-26T12:00:00", XMR),
    ]
    summaries = build_summaries(records, TODAY, NY)
    assert flags(row(summaries.weekly, "2026-W44")) == (True, True)


def test_a_period_of_only_unpriced_records_is_zero_usd_and_flagged() -> None:
    summaries = build_summaries([rec("2026-10-20T18:45:10", 731_000_000_000)], TODAY, NY)
    week = row(summaries.weekly, "2026-W43")
    assert week.usd == Decimal(0)
    assert flags(week) == (False, True)


def test_final_prices_flag_nothing() -> None:
    summaries = build_summaries([rec("2026-06-10T08:30:00", XMR, "152.345")], TODAY, NY)
    for summary in (summaries.weekly, summaries.monthly, summaries.annual):
        assert all(flags(p) == (False, False) for p in (*summary.periods, summary.total))


def test_total_flags_are_any_of_their_periods() -> None:
    records = [
        rec("2025-03-14T09:00:00", XMR),  # unpriced, but only in the annual range
        rec("2026-10-27T11:00:00", 2 * XMR, "163.4", "provisional"),
        rec("2026-06-10T08:30:00", XMR, "152.345"),
    ]
    summaries = build_summaries(records, TODAY, NY)
    for summary in (summaries.weekly, summaries.monthly, summaries.annual):
        assert summary.total.provisional == any(p.provisional for p in summary.periods)
        assert summary.total.unpriced == any(p.unpriced for p in summary.periods)
    assert flags(summaries.weekly.total) == (True, False)
    assert flags(summaries.monthly.total) == (True, False)
    assert flags(summaries.annual.total) == (True, True)


def test_a_flagged_record_outside_the_range_flags_nothing() -> None:
    records = [
        rec("2019-01-10T12:00:00", XMR),
        rec("2019-02-10T12:00:00", XMR, "50", "provisional"),
    ]
    summaries = build_summaries(records, TODAY, NY)
    for summary in (summaries.weekly, summaries.monthly, summaries.annual):
        assert all(flags(p) == (False, False) for p in (*summary.periods, summary.total))


# Record checks (FR-018, research R10)


@pytest.mark.parametrize(
    ("record", "words"),
    [
        # "amount_piconero is a non-negative int"
        (ExportRecord("bad-tx", 1, -1, ts("2026-05-05T12:00:00"), None, None), "invalid amount"),
        # "usd_price is None or a finite Decimal > 0"
        (rec("2026-05-05T12:00:00", XMR, "NaN", txid="bad-tx"), "invalid price"),
        (rec("2026-05-05T12:00:00", XMR, "0", txid="bad-tx"), "invalid price"),
        (rec("2026-05-05T12:00:00", XMR, "-1", txid="bad-tx"), "invalid price"),
        # "price_status is None exactly when the price is"
        (
            ExportRecord("bad-tx", 1, XMR, ts("2026-05-05T12:00:00"), None, "final"),
            "invalid price status",
        ),
        (
            ExportRecord("bad-tx", 1, XMR, ts("2026-05-05T12:00:00"), Decimal(150), None),
            "invalid price status",
        ),
        (
            ExportRecord("bad-tx", 1, XMR, ts("2026-05-05T12:00:00"), Decimal(150), "settled"),  # type: ignore[arg-type]
            "invalid price status",
        ),
        (ExportRecord("bad-tx", 1, XMR, 10**20, None, None), "invalid moment"),
    ],
)
def test_check_record_rejects_broken_records(record: ExportRecord, words: str) -> None:
    with pytest.raises(SummaryDataError, match="bad-tx") as raised:
        check_record(record)
    assert words in str(raised.value)
