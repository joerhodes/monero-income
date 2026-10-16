"""Turn the wallet's raw ``in`` list into typed entries. Pure: no I/O."""

import re

from monero_income.primitives.errors import WalletResponseError
from monero_income.primitives.models import IncomingEntry

_TXID = re.compile(r"[0-9a-fA-F]{64}")


def parse_incoming(raw: object) -> list[IncomingEntry]:
    """Parse the raw ``in`` list from ``get_transfers``.

    ``None`` means the wallet omitted the list, which it does when it is empty.
    Anything malformed raises ``WalletResponseError``.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise WalletResponseError("incoming list is not a JSON array")
    return [_parse_entry(item, index) for index, item in enumerate(raw)]


def _parse_entry(item: object, index: int) -> IncomingEntry:
    if not isinstance(item, dict):
        raise WalletResponseError(f"incoming entry {index} is not a JSON object")
    txid = item.get("txid")
    if not isinstance(txid, str) or not _TXID.fullmatch(txid):
        raise WalletResponseError(f"incoming entry {index} has an invalid txid")
    height = _non_negative_int(item, "height", index)
    if height == 0:
        raise WalletResponseError(f"incoming entry {index} has height 0")
    return IncomingEntry(
        txid=txid.lower(),
        height=height,
        amount_piconero=_non_negative_int(item, "amount", index),
        timestamp=_non_negative_int(item, "timestamp", index),
    )


def _non_negative_int(item: dict[object, object], field: str, index: int) -> int:
    value = item.get(field)
    # bool is a subclass of int, and a JSON float such as 1.0 must not pass as an int.
    if type(value) is not int:
        raise WalletResponseError(f"incoming entry {index} has a missing or non-integer {field}")
    if value < 0:
        raise WalletResponseError(f"incoming entry {index} has a negative {field}")
    return value
