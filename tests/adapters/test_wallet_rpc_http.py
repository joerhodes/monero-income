"""HttpWalletRpc against httpx.MockTransport: real HTTP handling, no sockets."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from monero_income.primitives.errors import (
    WalletError,
    WalletLoginError,
    WalletResponseError,
    WalletRpcError,
    WalletUnreachableError,
)
from monero_income.primitives.wallet_rpc import HttpWalletRpc

URL = "http://127.0.0.1:18088/json_rpc"
PASSWORD = "pw-Zq9!secret"
DIGEST_CHALLENGE = 'Digest realm="monero-rpc", nonce="abc123", qop="auth", algorithm=MD5'

Handler = Callable[[httpx.Request], httpx.Response]


def wallet(handler: Handler, username: str | None = None) -> HttpWalletRpc:
    return HttpWalletRpc(URL, username, PASSWORD, transport=httpx.MockTransport(handler))


def result(value: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": "0", "result": value})


class Recorder:
    """Records request bodies and answers with a fixed result."""

    def __init__(self, value: dict[str, Any]) -> None:
        self.value = value
        self.bodies: list[dict[str, Any]] = []
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.bodies.append(json.loads(request.content))
        return result(self.value)


def test_get_height_posts_json_rpc_and_returns_height() -> None:
    recorder = Recorder({"height": 3_210_000})

    assert wallet(recorder).get_height() == 3_210_000
    assert recorder.bodies == [{"jsonrpc": "2.0", "id": "0", "method": "get_height", "params": {}}]
    assert recorder.requests[0].url == URL


def test_get_transfers_sends_exact_params_and_returns_raw_in_list() -> None:
    entries = [{"txid": "ab" * 32, "height": 5, "amount": 1, "timestamp": 2}]
    recorder = Recorder({"in": entries})

    response = wallet(recorder).get_transfers(100, 10_100)

    assert recorder.bodies[0]["method"] == "get_transfers"
    # Exact params. "out": false is the test for FR-003 (outgoing never fetched), and no
    # account_index/all_accounts key means account 0 only (spec Assumptions).
    assert recorder.bodies[0]["params"] == {
        "in": True,
        "out": False,
        "pending": False,
        "failed": False,
        "pool": False,
        "filter_by_height": True,
        "min_height": 100,
        "max_height": 10_100,
    }
    assert response.incoming == entries


def test_absent_in_list_is_none() -> None:
    assert wallet(Recorder({})).get_transfers(0, 10).incoming is None


def test_requests_use_a_20_second_timeout() -> None:
    recorder = Recorder({"height": 1})

    wallet(recorder).get_height()

    timeout = recorder.requests[0].extensions["timeout"]
    assert timeout == {"connect": 20.0, "read": 20.0, "write": 20.0, "pool": 20.0}


def test_digest_challenge_is_answered() -> None:
    authorizations: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        authorizations.append(request.headers.get("Authorization"))
        if "Authorization" not in request.headers:
            return httpx.Response(401, headers={"WWW-Authenticate": DIGEST_CHALLENGE})
        return result({"height": 42})

    assert wallet(handler, username="monero").get_height() == 42
    assert authorizations[0] is None
    assert authorizations[1] is not None
    assert authorizations[1].startswith('Digest username="monero"')
    assert PASSWORD not in authorizations[1]


def always_401(request: httpx.Request) -> httpx.Response:
    return httpx.Response(401, headers={"WWW-Authenticate": DIGEST_CHALLENGE})


def connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("[Errno 61] Connection refused", request=request)


def read_timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timed out", request=request)


def http_500(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="Internal Server Error")


def not_json(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, text="<html>hello</html>")


def missing_result(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"jsonrpc": "2.0", "id": "0"})


def rpc_error(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, json={"jsonrpc": "2.0", "id": "0", "error": {"code": -13, "message": "No wallet file"}}
    )


@pytest.mark.parametrize(
    ("handler", "username", "expected"),
    [
        (always_401, "monero", WalletLoginError),
        (always_401, None, WalletLoginError),  # login required but none configured
        (connect_error, None, WalletUnreachableError),
        (read_timeout, None, WalletUnreachableError),
        (http_500, None, WalletResponseError),
        (not_json, None, WalletResponseError),
        (missing_result, None, WalletResponseError),
        (rpc_error, None, WalletRpcError),
    ],
)
def test_failures_map_to_wallet_errors(
    handler: Handler, username: str | None, expected: type[WalletError]
) -> None:
    with pytest.raises(expected) as excinfo:
        wallet(handler, username=username).get_transfers(0, 10)

    assert PASSWORD not in str(excinfo.value)


def test_rpc_error_keeps_code_and_message() -> None:
    with pytest.raises(WalletRpcError) as excinfo:
        wallet(rpc_error).get_height()

    assert excinfo.value.code == -13
    assert excinfo.value.message == "No wallet file"


@pytest.mark.parametrize("height", [None, "12", -1, True, 1.5])
def test_invalid_height_is_a_response_error(height: object) -> None:
    with pytest.raises(WalletResponseError):
        wallet(Recorder({"height": height})).get_height()
