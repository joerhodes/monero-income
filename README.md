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

Feature 001 records the wallet's incoming transactions in a local SQLite
database. USD pricing and reports come in later features.

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
```

If the file holds a password, keep it private:

```sh
chmod 600 ~/.config/monero-income/config.toml
```

The tool warns if the file is readable by other users. A password without a
username is an error, and `rpc_url` must not contain credentials.

### Run

```sh
monero-income [--rpc-url URL] [--username NAME] [--db-path PATH]
```

Every run starts with a sync, which records new incoming transactions from
account 0 of the wallet. It prints one line:

```text
Recorded 3 new transactions.
No new transactions found.
```

Running it again is safe: only new transactions are added, and recorded ones
are never changed. If a run is interrupted, the next run picks up where it
left off.

Errors print a single `Error: …` line on standard error, never a traceback.
Exit status: `0` success, `1` error, `2` command-line usage error, `130`
interrupted (Ctrl-C).
