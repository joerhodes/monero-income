# Contract: price source (CoinGecko `/coins/{id}/history`)

## Protocol (primitives; orchestration depends only on this)

```python
class PriceSource(Protocol):
    def daily_price(self, day: date) -> PriceAnswer: ...

PriceAnswer = Price | NoPrice | OutsideHistory   # frozen dataclasses
#   Price(usd_price: Decimal)
#   NoPrice(reason: str)        # 200 without usable market_data, or a malformed/zero/negative price
#   OutsideHistory()            # 401 with error_code 10012
```

Run-stopping outcomes are raised, not returned:

| Exception (primitives/errors.py) | Cause |
|----------------------------------|-------|
| `PriceRateLimitedError(retry_after: float \| None)` | HTTP 429 |
| `PriceKeyRejectedError` | HTTP 401 whose body isn't `error_code` 10012 |
| `PriceUnavailableError(reason)` | connect error, timeout (20 s), other non-2xx, non-JSON body |

The retry-once-after-backoff policy and the pacing live in **orchestration**, so the client
makes exactly one HTTP request per call (constitution IV).

## Request

```text
GET {coingecko_url}/coins/{coin_id}/history?date={dd-mm-yyyy}&localization=false
Header: x-cg-demo-api-key: {key}   # key type "demo"
   or: x-cg-pro-api-key: {key}    # key type "pro" (the legacy header); no key header without a key
Header: accept: application/json
Timeout: 20 s
```

## Response handling

1. Read the body. Decode it with `json.loads(content, parse_float=Decimal)`, never
   `response.json()`.
2. On HTTP 401, if the body's `error.status.error_code` is `10012`, return `OutsideHistory()`.
   Also accept `status.error_code` or a top-level `error_code`. The observed body is
   `{"error": {"status": {"error_code": 10012, "error_message": "…"}}}` (research R3).
   Otherwise raise `PriceKeyRejectedError`. Classify only after reading the body.
3. On HTTP 429, raise `PriceRateLimitedError`, with `Retry-After` parsed when present.
4. On other non-2xx, raise `PriceUnavailableError(f"HTTP {status}")`.
5. On 200, `parse_history_price(body)`, which is pure, reads
   `body["market_data"]["current_price"]["usd"]`:
   - missing at any level → `NoPrice("no price for this date")`;
   - `Decimal`, or `int` (not `bool`), finite and > 0 → `Price`;
   - anything else → `NoPrice("invalid price")`.

No message, exception, or log line includes the key. Exception text is built from the status,
the reason, and the date only.

## Test double

`tests/fakes/price_source.py` provides `FakePriceSource`, which maps `date` → `PriceAnswer`
or an exception to raise (one-shot or repeating) and records the requested dates in order.
The client's own tests use `httpx.MockTransport`.
