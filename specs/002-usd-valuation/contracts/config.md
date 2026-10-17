# Contract: config keys added by feature 002

These keys are added to [feature 001's config file](../../001-sync-incoming-transactions/contracts/config.md).
Its rules (precedence, missing file, permissions warning, unknown-key warning) are unchanged.
`coingecko_api_key` and `coingecko_api_key_type` can also be given on the command line
(contracts/cli.md), which overrides the file; the other keys are config file only.

```toml
coingecko_api_key      = "CG-…"     # optional
coingecko_api_key_type = "demo"     # "demo" or "pro"; required when a key is set
coingecko_url          = "https://api.coingecko.com/api/v3"   # default depends on key type
coin_id                = "monero"   # default shown
min_request_delay      = 0.7        # optional; seconds between price requests
```

| Key | Type | Default | Validation |
|-----|------|---------|------------|
| `coingecko_api_key` | string | none | Non-empty if present. **Never** appears in any output, error, warning, or `repr` |
| `coingecko_api_key_type` | string | none | `demo` or `pro`. Required when a key is set (`invalid coingecko_api_key_type: required when coingecko_api_key is set`); ignored with a warning when no key is set |
| `coingecko_url` | string | `https://pro-api.coingecko.com/api/v3` for `pro`, otherwise `https://api.coingecko.com/api/v3` | `http`/`https`, has a host, no user info (same rule as `rpc_url`) |
| `coin_id` | string | `monero` | non-empty, `[a-z0-9-]+` |
| `min_request_delay` | number (TOML int or float) | 0.7 with a key, 6.0 without ([research R1](../research.md)) | ≥ 0 and ≤ 60. Converted with `Decimal(str(value))`: it's a duration, not money |

The key type selects the header: `demo` → `x-cg-demo-api-key`, `pro` → `x-cg-pro-api-key`
(research R3). `coingecko_url` and `coin_id` keep the legacy key names. The legacy code
always sent `x-cg-pro-api-key`, so legacy users with a Pro key set
`coingecko_api_key_type = "pro"`.
