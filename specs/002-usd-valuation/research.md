# Research: USD Valuation of Recorded Transactions

**Feature**: 002-usd-valuation | **Date**: 2026-10-17

The planning input fixed most decisions; this file researches the one item marked OPEN
(pacing) and records findings that affect the decided design. Sources: CoinGecko API docs,
[coins/{id}/history](https://docs.coingecko.com/v3.0.1/reference/coins-id-history),
[errors and rate limits](https://docs.coingecko.com/docs/errors-and-rate-limits.md), and
[keyless public API](https://docs.coingecko.com/docs/keyless-public-api.md), read 2026-10-17.

## R1. Request pacing (OPEN, resolved)

**Documented limits**

| Tier | Documented limit | Safe interval |
|------|------------------|---------------|
| Keyless (no API key) | "~10–30 calls/min (dynamic, varies by server load)", IP-based | 6.0 s (assumes the 10/min floor) |
| Demo (free API key) | "100 calls/min" (older third-party docs say 30/min) | 0.6 s at 100/min |

The legacy default of 1.2 s (50 calls/min) is within the Demo limit but above the keyless
range, so a keyless run at 1.2 s would expect 429s, failing SC-007.

**Decision**: the default interval depends on whether a key is configured. `min_request_delay`
(seconds) overrides both defaults.

- With `coingecko_api_key` (Demo or Pro): **0.7 s** (about 86 calls/min, under the Demo plan's
  100; paid plans allow more).
- Without a key: **6.0 s** (10 calls/min, the keyless floor).

**Check against the spec**

- SC-007 (0 rate-limit refusals): met by both defaults within the documented limits. If the
  Demo plan is really 30/min (as older sources say), 0.7 s would draw a 429. The run then
  stops pricing cleanly (FR-009), and the user can raise `min_request_delay`.
- SC-012 (365 days priced in under 5 minutes): needs an interval of at most 0.82 s.
  - With a key: 365 × 0.7 s ≈ 4 min 16 s. **Met.**
  - Without a key: 365 × 6.0 s ≈ 36.5 min. **Not met.** A keyless run that stayed within the
    documented limits can't meet SC-012 with one request per day. Even at the keyless ceiling
    (30/min, 2 s) it would take about 12 minutes.
  - The legacy 1.2 s: 365 × 1.2 s ≈ 7.3 min. **Not met** even with a key.

**Resolved (2026-10-17)**: SC-012 was amended to apply when an API key is configured
(option a). Keyless runs stay within the keyless limits (SC-007) and simply take longer. The
alternatives were a multi-day endpoint (`/market_chart/range`), which contradicts the decided
`/history` endpoint and returns different price points, and dropping SC-012.

**Alternatives considered**: one fixed default (1.2 s) breaks SC-007 without a key and SC-012
with one. An adaptive rate driven by 429s would spend requests on refusals; SC-007 asks for
none.

## R2. What `/coins/{id}/history` returns (finding)

- `GET {coingecko_url}/coins/{coin_id}/history?date=dd-mm-yyyy&localization=false`. The date
  is **day-month-year**, not ISO.
- "Data returned is a snapshot at `00:00:00 UTC` for the given date." So the source's daily
  price for date D is its price at the **start** of D, read from
  `market_data.current_price.usd`. This is "the price source's daily price for that UTC
  calendar date" (spec FR-003).
- "The last completed UTC day (00:00) becomes available 35 minutes after midnight (00:35
  UTC)." Before that, a request for the new day returns no `market_data`, which the design
  treats as "no price for this day" (a temporary failure; the next day is tried).
- **Consequence for settling**: the decided rule (settled 1 hour after D *ends*) keeps D
  provisional all through day D, even though the 00:00 snapshot for D is published at 00:35
  on D. The rule is conservative, not wrong: a price fetched during D is refreshed once after
  D+1 01:00 and then finalized. No change is proposed; noted so the extra refresh isn't
  mistaken for a bug.
- "Historical data via the Demo API is restricted to the past 365 days." The keyless page
  states no history limit; the design assumes the same 365 days. The decided 364-day cutoff
  keeps one day of margin.

## R3. Error classification (decided; documentation check)

- 429 means rate limited, and 401 means a missing or invalid key; both match the decisions.
- **`error_code` 10012 ("outside the history period")** isn't in the public error-code list,
  but a manual request on 2026-10-17 confirmed it, and the body shape:
  `{"error": {"status": {"error_code": 10012, "error_message": "Your request exceeds the
  allowed time range. Public API users are limited to querying historical data within the
  past 365 days. …"}}}`. That also confirms the 365-day limit applies to keyless use. The
  client reads `error.status.error_code` and, for robustness, also `status.error_code` and a
  top-level `error_code`. A second manual request (`curl -s -o /dev/null -w '%{http_code}'`)
  confirmed the response status is **401**, matching the decided rule: a 401 carrying 10012
  means "outside history", and a 401 without it is treated as a rejected key.
- Whether a `Retry-After` header is sent isn't documented. The 429 backoff is fixed at
  **10 seconds**, enough to clear a per-minute window partly, and short enough to stay
  "brief". A `Retry-After` value up to 60 s is honoured if present.
- **API key header and key type (decided 2026-10-17)**: the legacy code sends
  `x-cg-pro-api-key`, on the assumption that only the Pro API needs a key. CoinGecko now has two
  key types with different headers, so the key type is configured alongside the key:

  | `coingecko_api_key_type` | Header | Default `coingecko_url` |
  |---|---|---|
  | `demo` | `x-cg-demo-api-key` | `https://api.coingecko.com/api/v3` |
  | `pro` | `x-cg-pro-api-key` | `https://pro-api.coingecko.com/api/v3` |

  The documentation says Pro keys are served from the `pro-api` host and Demo keys from the
  public host, so the key type also picks the default base URL. An explicit `coingecko_url`
  still wins. The type is required whenever a key is set, so the header is never guessed. Both
  the key and its type can also be given on the command line (decided). The command-line key
  is a convenience, and FR-015 is still met because the config file remains a way to supply it
  off the command line. A key given on the command line can still show up in shell history
  and process listings, so the README recommends the config file.
- **History cutoff with a Pro key**: paid plans have longer history, but the 364-day cutoff
  applies regardless of key type (confirmed 2026-10-17). Lifting it for Pro keys is a future
  enhancement, out of scope for feature 002.

## R4. Exact decimal handling (finding)

- `httpx.Response.json()` parses numbers as `float`. The client must decode the body with
  `json.loads(response.content, parse_float=Decimal)`, so `"usd": 152.3456` arrives as
  `Decimal("152.3456")` exactly. An integer price (`152`) arrives as `int` and is converted
  with `Decimal(int)`. `bool`, `NaN`/`Infinity`, zero, and negative values are rejected
  (FR-016).
- Python's default decimal context rounds to 28 significant digits. A piconero amount (up to
  20 digits) times a price with many digits can exceed that, so valuation rounds silently
  under the default context. `usd_value()` therefore computes under a local context with
  precision large enough for the operands and the `Inexact` trap set, then shifts by 10⁻¹²
  with `scaleb(-12)`, which is exact. Any rounding raises instead of passing silently
  (constitution III, SC-002).
- Prices are stored as the canonical decimal text of the parsed `Decimal` (`str(price)`),
  which round-trips exactly. Exponent forms such as `1.5E+2` are normalized away by
  formatting with `format(price, "f")`.

## R5. CSV import parsing (decided; details)

- Read with `open(path, encoding="utf-8-sig", newline="")`, so a leading BOM from spreadsheet
  exports is tolerated, then `csv.reader`. The header must be exactly
  `date_utc,usd_price` (whitespace around names is trimmed).
- `usd_price` must match `^[0-9]+(\.[0-9]+)?$` before `Decimal()` is called. That rejects
  exponents, signs, `NaN`, and thousands separators, and then the value must be greater than
  0. `date_utc` must parse with `date.fromisoformat` and be exactly `YYYY-MM-DD`.
- Row numbers in errors are the file's line numbers (header = line 1), so "line 7" points at
  what a user sees in an editor.
