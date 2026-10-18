"""The pricing step: look up each day that needs a price, oldest first, and record it."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from monero_income.orchestration.valuation import plan_lookups, price_status
from monero_income.primitives.models import DailyPrice
from monero_income.primitives.price_parse import NoPrice, OutsideHistory, Price
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
    """Price every day with transactions and no final price; one commit per price."""
    plan = plan_lookups(price_needs(conn), today)
    priced = provisional = no_price = not_refreshed = 0
    too_old = len(plan.too_old)

    for need in plan.requestable:
        answer = source.daily_price(need.date_utc)
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
    )
