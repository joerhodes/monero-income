# Contract: monero-wallet-rpc usage

The tool is a client of a user-run `monero-wallet-rpc`, over JSON-RPC 2.0 at `rpc_url`
(`POST`, `Content-Type: application/json`). It uses HTTP Digest auth when `username` is set,
with a 20-second timeout per request. See [research.md](../research.md) R2, R5, R6.

## Protocol (primitives, the only thing orchestration depends on)

```python
class WalletRpc(Protocol):
    def get_height(self) -> int: ...
    def get_transfers(self, min_height: int, max_height: int) -> TransfersResponse: ...
```

`TransfersResponse` holds the raw `in` entry list as returned (JSON values). Parsing into
`IncomingEntry` is a separate pure function.

## Calls

### `get_height`

```json
{"jsonrpc": "2.0", "id": "0", "method": "get_height", "params": {}}
```

Uses `result.height` (int): the wallet's scanned chain height.

### `get_transfers` (one call per height window)

```json
{"jsonrpc": "2.0", "id": "0", "method": "get_transfers", "params": {
  "in": true, "out": false, "pending": false, "failed": false, "pool": false,
  "filter_by_height": true, "min_height": LO, "max_height": HI
}}
```

- Returns entries with `LO < height <= HI` (`min_height` is exclusive).
- No `account_index` or `all_accounts` is sent, so the wallet returns **account 0 only**. This
  is intended: the spec's Assumptions limit the tool to account 0, where mining payouts
  arrive.
- Fields used from each `in` entry: `txid`, `height`, `amount`, `timestamp`.
- An absent `in` key means an empty list. The server omits empty lists.

## Error mapping

| Wallet behavior | Error raised (primitives) | User-facing category |
|-----------------|---------------------------|----------------------|
| Connection refused, DNS failure, timeout | `WalletUnreachableError` | Wallet unreachable |
| HTTP `401` after the digest handshake (or no username given) | `WalletLoginError` | Login rejected |
| Other non-2xx HTTP status | `WalletResponseError` | Invalid wallet response |
| Body not JSON, or missing `result` | `WalletResponseError` | Invalid wallet response |
| JSON-RPC `error` object | `WalletRpcError(code, message)` | Wallet error |
| Entry fails parsing (see data-model.md) | `WalletResponseError` | Invalid wallet response |

## Test double

`tests/fakes/wallet.py` provides `FakeWalletRpc`. It holds incoming entries and a height,
answers `get_transfers` with the server's exact bound semantics, and can be told to raise any
of the errors above on the Nth call (to simulate interruption). The HTTP adapter's own tests
use `httpx.MockTransport`, with no sockets.
