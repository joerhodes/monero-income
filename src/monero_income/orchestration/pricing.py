"""The pricing step: look up each day that needs a price, oldest first, and record it."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from monero_income.orchestration.valuation import plan_lookups, price_status
from monero_income.primitives.errors import (
    PriceKeyRejectedError,
    PriceRateLimitedError,
    PriceSourceError,
    PriceUnavailableError,
)
from monero_income.primitives.models import DailyPrice
from monero_income.primitives.price_parse import NoPrice, OutsideHistory, Price, PriceAnswer
from monero_income.primitives.price_source import PriceSource
from monero_income.primitives.prices_db import all_days_final, price_needs, upsert_price


@dataclass(frozen=True)
class StopReason:
    """Why pricing stopped early. ``reason`` never includes the API key."""

    kind: Literal["rate_limited", "key_rejected", "unavailable"]
    reason: str


@dataclass(frozen=True)
class PricingSummary:
    priced: int = 0  # prices recorded this run
    provisional: int = 0  # of those, how many are provisional
    no_price: int = 0  # days with no price, to be retried
    not_refreshed: int = 0  # provisional prices this run couldn't refresh
    too_old: int = 0  # days older than the price history
    all_final: bool = False  # at least one transaction, and every day has a final price
    stopped: StopReason | None = None


def price_days(
    conn: sqlite3.Connection,
    source: PriceSource,
    *,
    today: date,
    clock: Callable[[], datetime],
    sleep: Callable[[float], None],
    delay: Decimal,
) -> PricingSummary:
    """Price every day with transactions and no final price; one commit per price.

    Requests are paced ``delay`` seconds apart. A rate limit is retried once after a
    backoff; a second one, a rejected key, or an unreachable source stops pricing for
    this run without failing it (FR-009). Storage errors and ``KeyboardInterrupt``
    propagate; prices already recorded are kept either way.
    """
    plan = plan_lookups(price_needs(conn), today)
    pacer = _Pacer(clock, sleep, delay)
    priced = provisional = no_price = not_refreshed = 0
    too_old = len(plan.too_old)
    stopped: StopReason | None = None

    for index, need in enumerate(plan.requestable):
        try:
            answer = _look_up(source, need.date_utc, pacer, sleep)
        except PriceSourceError as error:
            stopped = _stop_reason(error)
            remaining = plan.requestable[index:]
            not_refreshed += sum(need.has_provisional for need in remaining)
            no_price += sum(not need.has_provisional for need in remaining)
            break
        match answer:
            case Price(usd_price=usd_price):
                now = clock()
                status = price_status(need.date_utc, now)
                upsert_price(
                    conn,
                    DailyPrice(
                        date_utc=need.date_utc,
                        usd_price=usd_price,
                        status=status,
                        source="api",
                        fetched_at=int(now.timestamp()),
                    ),
                )
                priced += 1
                provisional += status == "provisional"
            case NoPrice():
                if need.has_provisional:
                    not_refreshed += 1
                else:
                    no_price += 1
            case OutsideHistory():
                too_old += 1

    return PricingSummary(
        priced=priced,
        provisional=provisional,
        no_price=no_price,
        not_refreshed=not_refreshed,
        too_old=too_old,
        all_final=all_days_final(conn),
        stopped=stopped,
    )


RATE_LIMIT_BACKOFF = 10.0  # seconds, when the source doesn't say (research R3)
MAX_RATE_LIMIT_BACKOFF = 60.0


def _look_up(
    source: PriceSource, day: date, pacer: "_Pacer", sleep: Callable[[float], None]
) -> PriceAnswer:
    """One paced request, retried once after a backoff if rate-limited."""
    pacer.wait()
    try:
        return source.daily_price(day)
    except PriceRateLimitedError as error:
        backoff = min(error.retry_after or RATE_LIMIT_BACKOFF, MAX_RATE_LIMIT_BACKOFF)
        sleep(backoff)
        pacer.wait()
        return source.daily_price(day)  # a second rate limit propagates and stops pricing


class _Pacer:
    """Keeps request starts at least ``delay`` seconds apart; never sleeps before the first."""

    def __init__(
        self, clock: Callable[[], datetime], sleep: Callable[[float], None], delay: Decimal
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._delay = float(delay)
        self._last: datetime | None = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self._delay - (self._clock() - self._last).total_seconds()
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()


def _stop_reason(error: PriceSourceError) -> StopReason:
    match error:
        case PriceRateLimitedError():
            return StopReason("rate_limited", "the price source is rate-limiting requests")
        case PriceKeyRejectedError():
            return StopReason("key_rejected", "the price source rejected the API key")
        case PriceUnavailableError():
            return StopReason("unavailable", f"cannot reach the price source: {error.reason}")
        case _:
            return StopReason("unavailable", f"cannot reach the price source: {error}")
