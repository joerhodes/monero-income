"""Client for CoinGecko's `/coins/{id}/history` endpoint.

Each call makes exactly one request and classifies the response; retrying and
pacing belong to orchestration (constitution IV). The body is decoded with
``parse_float=Decimal`` so prices arrive exact (constitution III). No error
message ever includes the API key.
"""

import json
from datetime import date
from decimal import Decimal
from typing import Literal, Protocol

import httpx

from monero_income.primitives.errors import (
    PriceKeyRejectedError,
    PriceRateLimitedError,
    PriceUnavailableError,
)
from monero_income.primitives.price_parse import OutsideHistory, PriceAnswer, parse_history_price

OUTSIDE_HISTORY_ERROR_CODE = 10012
_KEY_HEADERS = {"demo": "x-cg-demo-api-key", "pro": "x-cg-pro-api-key"}


class PriceSource(Protocol):
    def daily_price(self, day: date) -> PriceAnswer: ...


class CoinGeckoPriceSource:
    """``PriceSource`` over HTTP. The key type picks the header (research R3)."""

    def __init__(
        self,
        base_url: str,
        coin_id: str,
        api_key: str | None,
        api_key_type: Literal["demo", "pro"] | None,
        timeout: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        headers = {"accept": "application/json"}
        if api_key is not None and api_key_type is not None:
            headers[_KEY_HEADERS[api_key_type]] = api_key
        self._url = f"{base_url.rstrip('/')}/coins/{coin_id}/history"
        self._timeout = timeout
        self._client = httpx.Client(
            headers=headers, timeout=httpx.Timeout(timeout), transport=transport
        )

    def close(self) -> None:
        self._client.close()

    def daily_price(self, day: date) -> PriceAnswer:
        params = {"date": day.strftime("%d-%m-%Y"), "localization": "false"}
        try:
            response = self._client.get(self._url, params=params)
        except httpx.TimeoutException as error:
            raise PriceUnavailableError(f"no answer within {self._timeout:g} seconds") from error
        except httpx.TransportError as error:
            # httpx's message names the host and cause, never headers, so never the key.
            raise PriceUnavailableError(str(error) or type(error).__name__) from error

        body = _decode(response.content)  # read the body before classifying a 401
        if response.status_code == 401:
            if _error_code(body) == OUTSIDE_HISTORY_ERROR_CODE:
                return OutsideHistory()
            raise PriceKeyRejectedError()
        if response.status_code == 429:
            raise PriceRateLimitedError(_retry_after(response.headers.get("Retry-After")))
        if not response.is_success:
            raise PriceUnavailableError(f"HTTP {response.status_code}")
        if body is None:
            raise PriceUnavailableError("the response is not JSON")
        return parse_history_price(body)


def _decode(content: bytes) -> object | None:
    try:
        decoded: object = json.loads(content, parse_float=Decimal)
    except ValueError:
        return None
    return decoded


def _error_code(body: object) -> object:
    """``error_code`` from any of the shapes CoinGecko uses (research R3)."""
    if not isinstance(body, dict):
        return None
    for container in (
        _dict(_dict(body.get("error")).get("status")),
        _dict(body.get("status")),
        body,
    ):
        if "error_code" in container:
            return container["error_code"]
    return None


def _dict(value: object) -> dict[object, object]:
    return value if isinstance(value, dict) else {}


def _retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return seconds if seconds >= 0 else None
