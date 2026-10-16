"""In-memory stand-in for monero-wallet-rpc, matching its get_transfers bounds."""

import hashlib
from dataclasses import dataclass, field
from typing import Any

from monero_income.primitives.wallet_rpc import TransfersResponse, WalletRpc


def entry(
    txid_seed: str,
    height: int,
    amount: int,
    timestamp: int = 1_700_000_000,
    subaddr_minor: int = 0,
) -> dict[str, Any]:
    """A valid raw ``in`` entry. The same seed always gives the same 64-hex txid."""
    return {
        "txid": hashlib.sha256(txid_seed.encode()).hexdigest(),
        "height": height,
        "amount": amount,
        "timestamp": timestamp,
        "type": "in",
        "subaddr_index": {"major": 0, "minor": subaddr_minor},
    }


@dataclass
class FakeWalletRpc:
    """Holds raw incoming entries and a chain height.

    ``get_transfers`` returns entries with ``min_height < height <= max_height``,
    like the real wallet (``min_height`` is exclusive), and logs each call's bounds.
    Set ``fail_on_call`` (1-based) and ``failure`` to raise on that call; the
    failure may be any exception, including ``KeyboardInterrupt``.
    """

    entries: list[dict[str, Any]] = field(default_factory=list)
    height: int = 0
    fail_on_call: int | None = None
    failure: BaseException = field(default_factory=lambda: RuntimeError("injected failure"))
    calls: list[tuple[int, int]] = field(default_factory=list)

    def get_height(self) -> int:
        return self.height

    def get_transfers(self, min_height: int, max_height: int) -> TransfersResponse:
        self.calls.append((min_height, max_height))
        if self.fail_on_call is not None and len(self.calls) == self.fail_on_call:
            raise self.failure
        matching = [e for e in self.entries if min_height < e["height"] <= max_height]
        # The real wallet omits an empty list.
        return TransfersResponse(incoming=matching or None)


def _satisfies_protocol(fake: FakeWalletRpc) -> WalletRpc:
    return fake  # mypy checks FakeWalletRpc against the WalletRpc Protocol here
