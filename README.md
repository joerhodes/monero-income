# monero-income

A command-line tool that builds weekly and monthly income reports from a
Monero wallet, valuing each payout at its historical USD price.

## Intro

This is a spec-driven development (SDD) rewrite of one of my existing
projects. The rewrite has two goals:

- Try out [GitHub Spec Kit](https://github.com/github/spec-kit) for SDD,
  from constitution through implementation.
- Deliver a few items from the original project's roadmap: price
  finalization for recent days, and default row limits on the weekly and
  monthly tables.

The original version remains the reference implementation. This rewrite
is expected to produce matching reports for the same data.

## Status

Feature 001 (wallet sync) in complete.

## Usage

Every run records the wallet's incoming transactions in a local SQLite
database (feature 001), then values them in USD using daily prices from
CoinGecko (feature 002). CSV output and summaries come in later features.

### Install

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync                    # from a checkout, then run with: uv run monero-income
uv tool install .          # or install the monero-income command for your user
```

### Configure

The tool talks to a `monero-wallet-rpc` that you run, with the wallet open.
Settings come from command-line options, then the config file
`~/.config/monero-income/config.toml`, then defaults. The config file is
optional:

```toml
rpc_url  = "http://127.0.0.1:18088/json_rpc"    # default shown
username = "monero"                              # if the wallet RPC uses --rpc-login
password = "secret"                              # config file only; never on the command line
db_path  = "~/.local/share/monero-income/xmr.db" # default shown

# USD prices (CoinGecko). A key is optional; a free Demo key allows faster pricing.
coingecko_api_key      = "CG-..."   # optional
coingecko_api_key_type = "demo"     # "demo" or "pro"; required when a key is set
coingecko_url          = "https://api.coingecko.com/api/v3"  # default; pro-api.coingecko.com for "pro"
coin_id                = "monero"   # default shown
min_request_delay      = 2.5        # optional; seconds between price requests
```

If the file holds a password or an API key, keep it private:

```sh
chmod 600 ~/.config/monero-income/config.toml
```

The tool warns if the file is readable by other users. A password without a
username is an error, and `rpc_url` must not contain credentials. The API key
and its type can also be given with `--coingecko-api-key` and
`--coingecko-api-key-type`, but prefer the config file: a key typed on the
command line can end up in your shell history. The key is never shown in any
output.

Price requests are paced to stay within CoinGecko's limits: 2.5 seconds apart
with a key, 6 seconds without. `min_request_delay` overrides both.

### Run

```sh
monero-income [--rpc-url URL] [--username NAME] [--db-path PATH]
              [--import-prices CSV]
              [--coingecko-api-key KEY] [--coingecko-api-key-type demo|pro]
```

Every run starts with a sync, which records new incoming transactions from
account 0 of the wallet. It then looks up the USD price for each UTC day that
has transactions but no final price, oldest day first. Each transaction is
valued at its day's price, exactly; rounding happens only on output. The run
prints the sync line and then whichever pricing lines apply:

```text
Recorded 3 new transactions.
Priced 4 days (1 provisional).
2 days still have no price; a later run will try again.
1 provisional price couldn't be refreshed; a later run will try again.
3 days are older than the price history and can't be looked up; use --import-prices to add them.
All transactions are valued.
```

Running it again is safe: only new transactions are added, and recorded ones
are never changed. If a run is interrupted, the next run picks up where it
left off.

#### Provisional and final prices

A day's price is provisional until one hour after that UTC day ends, and is
refreshed on each run until then. The first lookup after that records it as
final, and a final price never changes. If the tool isn't run for a while, the
next run refreshes and finalizes the days it missed.

#### When the price source has problems

If CoinGecko is unreachable, rejects the API key, or keeps rate-limiting after
one retry, the run prints a `Warning: price lookups stopped: …` line, keeps
every price already recorded, and still succeeds. The next run carries on.

#### Older days and `--import-prices`

CoinGecko only provides about a year of history, so days more than 364 days
old are never looked up. To value them, import daily prices from a CSV file:

```csv
date_utc,usd_price
2024-03-01,151.234
2024-03-02,149.9
```

`date_utc` is a UTC date (`YYYY-MM-DD`) and `usd_price` is USD per 1 XMR. The
whole file is checked first; any bad row rejects it, naming the line. Prices
are imported, as final, only for days older than the price history that have
no price yet; other rows are skipped and counted:

```text
Imported 2 prices; skipped 3 rows.
```

Errors print a single `Error: …` line on standard error, never a traceback.
Exit status: `0` success, `1` error, `2` command-line usage error, `130`
interrupted (Ctrl-C).
