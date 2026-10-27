"""Pure formatting and ordering of the export's rows (contracts/export-csv.md). No I/O.

Every value is exact except ``usd_value``, which is rounded to the cent, half up.
Decimals are written with format "f", never ``str()``, so no value has an exponent.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, localcontext

from monero_income.orchestration.valuation import usd_value
from monero_income.primitives.models import ExportRecord

HEADER = ("txid", "height", "timestamp_utc", "xmr", "usd_price", "price_status", "usd_value")
TBD = "TBD"
PICONERO_PER_XMR = 10**12
CENT = Decimal("0.01")

Row = tuple[str, str, str, str, str, str, str]


def format_timestamp(occurred_at: int) -> str:
    return datetime.fromtimestamp(occurred_at, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_xmr(amount_piconero: int) -> str:
    """Exactly 12 decimals, by integer arithmetic."""
    whole, fraction = divmod(amount_piconero, PICONERO_PER_XMR)
    return f"{whole}.{fraction:012d}"


def format_price(price: Decimal | None) -> str:
    return TBD if price is None else format(price, "f")


def round_cents(value: Decimal) -> Decimal:
    """Round to the cent, half up, in a context wide enough that only the cents round."""
    with localcontext() as context:
        # Digits before the point, plus two for the cents and one for a carry (9.995 → 10.00).
        context.prec = max(value.adjusted() + 1, 0) + 3
        return value.quantize(CENT, rounding=ROUND_HALF_UP)


def format_usd_value(amount_piconero: int, price: Decimal | None) -> str:
    if price is None:
        return TBD
    return format(round_cents(usd_value(amount_piconero, price)), "f")


def export_rows(records: Sequence[ExportRecord]) -> list[Row]:
    """One row per record in ``HEADER`` order, sorted by (timestamp, height, txid)."""
    ordered = sorted(records, key=lambda r: (r.occurred_at, r.height, r.txid))
    return [
        (
            r.txid,
            str(r.height),
            format_timestamp(r.occurred_at),
            format_xmr(r.amount_piconero),
            format_price(r.usd_price),
            r.price_status or TBD,
            format_usd_value(r.amount_piconero, r.usd_price),
        )
        for r in ordered
    ]
