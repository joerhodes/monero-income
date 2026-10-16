"""Client for a user-run monero-wallet-rpc (JSON-RPC 2.0 over HTTP).

Only fetches. The raw ``in`` list is returned as-is; parsing it is
``wallet_entries.parse_incoming`` (constitution IV).
"""

from dataclasses import dataclass
from typing import Protocol

import httpx

from monero_income.primitives.errors import (
    WalletLoginError,
    WalletResponseError,
    WalletRpcError,
    WalletUnreachableError,
)


@dataclass(frozen=True)
class TransfersResponse:
    """The raw ``in`` list from ``get_transfers``; ``None`` when the wallet omitted it."""

    incoming: object


class WalletRpc(Protocol):
    def get_height(self) -> int: ...

    def get_transfers(self, min_height: int, max_height: int) -> TransfersResponse:
        """Incoming entries with ``min_height < height <= max_height``."""
        ...


class HttpWalletRpc:
    """``WalletRpc`` over HTTP, with Digest auth when a username is given.

    Requests only incoming, confirmed entries, and sends no account parameters,
    so the wallet answers for account 0 only (spec Assumptions).
    """

    def __init__(
        self,
        url: str,
        username: str | None,
        password: str | None,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        auth = httpx.DigestAuth(username, password or "") if username is not None else None
        self._url = url
        self._timeout = timeout
        self._client = httpx.Client(auth=auth, timeout=httpx.Timeout(timeout), transport=transport)

    def close(self) -> None:
        self._client.close()

    def get_height(self) -> int:
        height = self._call("get_height", {}).get("height")
        if type(height) is not int or height < 0:
            raise WalletResponseError("get_height returned no valid height")
        return height

    def get_transfers(self, min_height: int, max_height: int) -> TransfersResponse:
        result = self._call(
            "get_transfers",
            {
                "in": True,
                "out": False,
                "pending": False,
                "failed": False,
                "pool": False,
                "filter_by_height": True,
                "min_height": min_height,
                "max_height": max_height,
            },
        )
        return TransfersResponse(incoming=result.get("in"))

    def _call(self, method: str, params: dict[str, object]) -> dict[str, object]:
        payload = {"jsonrpc": "2.0", "id": "0", "method": method, "params": params}
        try:
            response = self._client.post(self._url, json=payload)
        except httpx.TimeoutException as error:
            raise WalletUnreachableError(f"no answer within {self._timeout:g} seconds") from error
        except httpx.TransportError as error:
            raise WalletUnreachableError(str(error) or type(error).__name__) from error

        if response.status_code == 401:
            raise WalletLoginError("the wallet rejected the login")
        if not response.is_success:
            raise WalletResponseError(f"HTTP status {response.status_code}")
        try:
            body = response.json()
        except ValueError as error:
            raise WalletResponseError("the response is not JSON") from error
        if not isinstance(body, dict):
            raise WalletResponseError("the response is not a JSON object")

        rpc_error = body.get("error")
        if rpc_error is not None:
            if not isinstance(rpc_error, dict):
                raise WalletResponseError("malformed JSON-RPC error")
            code = rpc_error.get("code")
            message = rpc_error.get("message")
            raise WalletRpcError(
                code if type(code) is int else 0,
                message if isinstance(message, str) else "unknown error",
            )

        result = body.get("result")
        if not isinstance(result, dict):
            raise WalletResponseError(f"{method} returned no result")
        return result
