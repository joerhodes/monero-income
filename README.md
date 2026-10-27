# monero-income

A command-line tool that builds weekly and monthly income reports from a
Monero wallet, valuing each payout at its historical USD price.

## Intro

This is a spec-driven development (SDD) rewrite of a tool I originally
built by hand. The rewrite has two goals:

- Try out [GitHub Spec Kit](https://github.com/github/spec-kit) for SDD,
  from constitution through implementation, on a project small enough to
  finish and real enough to matter. I run it against my own wallet.
- Deliver a few items from the original project's roadmap along the way.

The original version is the reference for behavior. The rewrite matches it
except where a spec says otherwise: most notably, prices are looked up by
UTC day (the original used local dates, which was a bug), and recent prices
stay provisional until the day settles.

## Status and roadmap

| Feature | Status | What it covers |
|---|---|---|
| [001 wallet sync](specs/001-sync-incoming-transactions/) | Done | Records incoming transactions in SQLite; safe to re-run and resume |
| [002 USD valuation](specs/002-usd-valuation/) | Done | Daily CoinGecko prices, provisional/final pricing, CSV import for old days |
| [003 Transaction export](specs/003-transaction-csv-export) Done | Transaction CSV export |
| [004 …] | Planned | Weekly and monthly income tables |

## Where to look

The repo follows Spec Kit's layout:

- `.specify/memory/constitution.md`: the project's ground rules
  (Python style, single responsibility, testing expectations). Every plan is
  checked against it.
- `specs/NNN-name/`: one folder per feature, each with:
  - `spec.md`: what and why, no implementation details
  - `plan.md`: technical approach, checked against the constitution
  - `tasks.md`: the ordered task list that drove implementation
  - [`research.md`, `data-model.md`, `contracts/`, `quickstart.md` as present]
- `src/`, `tests/`: the implementation and its tests.
- `docs/sdd-log/`: my Claude Code sessions for every Spec Kit command, in
  the order they ran (`25-plan-002.md` is session 25, `/speckit.plan` for
  feature 002). The clarify and plan sessions show where requirements changed
  and why. For a good example, see the rate-limit conflict in
  [`25-plan-002.md`](docs/sdd-log/25-plan-002.md).

If you only read one feature, read
[002](specs/002-usd-valuation/spec.md). Provisional versus final prices
is where the spec did the most work.

## How I used AI

Claude wrote most of the code from the Spec Kit artifacts. My part
was the constitution, reviewing and revising each spec and plan before
implementation, and testing the results by hand against my own wallet.
I can explain and defend every design decision in this repo.

I started this experiment skeptical. SDD felt heavy for a tool this
size, and my habit with agentic editors is to hand them small, well-scoped
tasks one at a time. After implementing two features, I can see the appeal.
Once the constitution and the foundational spec were worked out, both the
code and later feature specs came together quickly. The planning phase
surfaced issues that could have become bugs, whether from conflicting
requirements or underspecified behavior, and they were fixed in the spec
before any code was written. 

For example, the plan for spec 002 showed that two of my success criteria 
couldn't both hold: without an API key, CoinGecko's rate limits make 
pricing a year of history in under five minutes impossible without being 
refused. I first limited the speed target to runs with a key, then dropped
it entirely. For a personal tool, a slow first run matters less than 
staying within the published limits and never losing a recorded price 
when a request is refused. I can see this method being a big benefit for 
new projects, and I expect that adding a constitution to an existing 
project would make new features and bug fixes go much more smoothly.

## Usage

Every run records the wallet's incoming transactions in a local SQLite
database (feature 001), then values them in USD using daily prices from
CoinGecko (feature 002), and writes them all to a CSV export (feature 003).
Summaries come in a later feature.

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
reports_path = "~/reports"                       # default shown; where the export is written

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
monero-income [--rpc-url URL] [--username NAME] [--db-path PATH] [--reports-path DIR]
              [--import-prices CSV]
              [--coingecko-api-key KEY] [--coingecko-api-key-type demo|pro]
```

Every run starts with a sync, which records new incoming transactions from
account 0 of the wallet. It then looks up the USD price for each UTC day that
has transactions but no final price, oldest day first. Each transaction is
valued at its day's price, exactly; rounding happens only on output. The run
prints the sync line, then whichever pricing lines apply, and last the export
line:

```text
Recorded 3 new transactions.
Priced 4 days (1 provisional).
2 days still have no price; a later run will try again.
1 provisional price couldn't be refreshed; a later run will try again.
3 days are older than the price history and can't be looked up; use --import-prices to add them.
All transactions are valued.
Exported 42 transactions to /Users/you/reports/xmr_income.csv.
```

Running it again is safe: only new transactions are added, and recorded ones
are never changed. If a run is interrupted, the next run picks up where it
left off.

#### The export

Every successful run writes `xmr_income.csv` to the reports directory
(`~/reports` unless `--reports-path` or `reports_path` says otherwise),
creating the directory if needed. The file lists every recorded transaction
with its day's USD price, price status, and USD value. It is replaced in full
on each run, never left half-written, and readable only by its owner. A run
that fails leaves the previous export unchanged. See
[docs/export-csv.md](docs/export-csv.md) for every column, the rounding rule,
and an example; that page is written so it can be handed to an accountant
along with the file.

The reports directory must be on a filesystem that supports file locking.
Some network shares don't, and the run fails there with a message saying so;
write the export to a local directory and copy it to the share.

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

## License

[MIT](LICENSE)
