"""CoinGeckoPriceSource against httpx.MockTransport: real HTTP handling, no sockets."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Literal

import httpx
import pytest

from monero_income.primitives.errors import (
    PriceKeyRejectedError,
    PriceRateLimitedError,
    PriceSourceError,
    PriceUnavailableError,
)
from monero_income.primitives.price_parse import NoPrice, OutsideHistory, Price
from monero_income.primitives.price_source import CoinGeckoPriceSource

URL = "https://api.coingecko.com/api/v3"
KEY = "CG-Zq9!distinctive-key"
DAY = date(2026, 10, 16)
PRICE_JSON = '{"id":"monero","market_data":{"current_price":{"usd":152.3456,"eur":140.1}}}'
OUTSIDE_JSON = (
    '{"error":{"status":{"timestamp":"2026-10-17T14:00:34.302+00:00","error_code":10012,'
    '"error_message":"Your request exceeds the allowed time range."}}}'
)

Handler = Callable[[httpx.Request], httpx.Response]


def source(
    handler: Handler,
    api_key: str | None = None,
    api_key_type: Literal["demo", "pro"] | None = None,
) -> CoinGeckoPriceSource:
    return CoinGeckoPriceSource(
        URL, "monero", api_key, api_key_type, transport=httpx.MockTransport(handler)
    )


class Recorder:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.response


def ok() -> Recorder:
    return Recorder(httpx.Response(200, text=PRICE_JSON))


def test_request_uses_the_history_endpoint_with_day_month_year() -> None:
    recorder = ok()

    source(recorder).daily_price(DAY)

    request = recorder.requests[0]
    assert request.method == "GET"
    assert request.url.path == "/api/v3/coins/monero/history"
    assert dict(request.url.params) == {"date": "16-10-2026", "localization": "false"}
    assert request.headers["accept"] == "application/json"
    assert request.extensions["timeout"] == {
        "connect": 20.0,
        "read": 20.0,
        "write": 20.0,
        "pool": 20.0,
    }


@pytest.mark.parametrize(
    ("key_type", "header", "other"),
    [
        ("demo", "x-cg-demo-api-key", "x-cg-pro-api-key"),
        ("pro", "x-cg-pro-api-key", "x-cg-demo-api-key"),
    ],
)
def test_key_header_follows_the_key_type(
    key_type: Literal["demo", "pro"], header: str, other: str
) -> None:
    recorder = ok()

    source(recorder, KEY, key_type).daily_price(DAY)

    assert recorder.requests[0].headers[header] == KEY
    assert other not in recorder.requests[0].headers


def test_no_key_header_without_a_key() -> None:
    recorder = ok()

    source(recorder).daily_price(DAY)

    headers = recorder.requests[0].headers
    assert "x-cg-demo-api-key" not in headers
    assert "x-cg-pro-api-key" not in headers


def test_price_is_decoded_exactly() -> None:
    answer = source(ok()).daily_price(DAY)

    assert answer == Price(Decimal("152.3456"))


def test_missing_market_data_is_no_price() -> None:
    answer = source(Recorder(httpx.Response(200, text='{"id":"monero"}'))).daily_price(DAY)

    assert answer == NoPrice("no price for this date")


@pytest.mark.parametrize(
    "body",
    [
        OUTSIDE_JSON,
        '{"status":{"error_code":10012,"error_message":"…"}}',
        '{"error_code":10012}',
    ],
)
def test_401_with_error_code_10012_is_outside_history(body: str) -> None:
    answer = source(Recorder(httpx.Response(401, text=body))).daily_price(DAY)

    assert answer == OutsideHistory()


@pytest.mark.parametrize(
    "body",
    ["", '{"error":{"status":{"error_code":10002,"error_message":"Missing API key"}}}', "nope"],
)
def test_other_401_means_the_key_was_rejected(body: str) -> None:
    with pytest.raises(PriceKeyRejectedError):
        source(Recorder(httpx.Response(401, text=body)), KEY, "demo").daily_price(DAY)


@pytest.mark.parametrize(("headers", "expected"), [({"Retry-After": "30"}, 30.0), ({}, None)])
def test_429_is_rate_limited(headers: dict[str, str], expected: float | None) -> None:
    with pytest.raises(PriceRateLimitedError) as excinfo:
        source(Recorder(httpx.Response(429, headers=headers))).daily_price(DAY)

    assert excinfo.value.retry_after == expected


def http_500(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="oops")


def not_json(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="<html>maintenance</html>")


def connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 8] nodename nor servname provided", request=request)


def read_timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timed out", request=request)


@pytest.mark.parametrize("handler", [http_500, not_json, connect_error, read_timeout])
def test_unusable_responses_are_unavailable(handler: Handler) -> None:
    with pytest.raises(PriceUnavailableError):
        source(handler).daily_price(DAY)


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_key_never_appears_in_errors(status: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=f'{{"error":"{KEY}"}}', headers={"X-Key": KEY})

    with pytest.raises(PriceSourceError) as excinfo:
        source(handler, KEY, "pro").daily_price(DAY)

    assert KEY not in str(excinfo.value)
    assert KEY not in repr(excinfo.value)
