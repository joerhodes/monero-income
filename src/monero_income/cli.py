"""Command-line interface: parse options, call run(), print the result.

No behavior lives here (constitution II); everything goes through
``monero_income.orchestration.run``.
"""

from typing import Annotated, NoReturn

import typer

from monero_income.orchestration import CliOptions, RunError, RunResult, run

app = typer.Typer(
    add_completion=False,
    pretty_exceptions_enable=False,
    help="Record a Monero wallet's incoming transactions locally.",
)


class StderrReporter:
    def warning(self, message: str) -> None:
        typer.echo(f"Warning: {message}", err=True)


@app.command()
def main_command(
    rpc_url: Annotated[
        str | None, typer.Option("--rpc-url", help="Wallet RPC address (URL).")
    ] = None,
    username: Annotated[
        str | None,
        typer.Option(
            "--username",
            help="Wallet RPC login name. The password is read from the config file only.",
        ),
    ] = None,
    db_path: Annotated[str | None, typer.Option("--db-path", help="SQLite database file.")] = None,
    import_prices: Annotated[
        str | None,
        typer.Option(
            "--import-prices",
            help="Import daily USD prices for old days from a CSV file (date_utc,usd_price).",
        ),
    ] = None,
    coingecko_api_key: Annotated[
        str | None,
        typer.Option(
            "--coingecko-api-key",
            help="Price source API key. Prefer the config file: a key given here can end up "
            "in shell history.",
        ),
    ] = None,
    coingecko_api_key_type: Annotated[
        str | None,
        typer.Option("--coingecko-api-key-type", help="Price source key type: demo or pro."),
    ] = None,
) -> None:
    options = CliOptions(
        rpc_url=rpc_url,
        username=username,
        db_path=db_path,
        import_prices=import_prices,
        coingecko_api_key=coingecko_api_key,
        coingecko_api_key_type=coingecko_api_key_type,
    )
    reporter = StderrReporter()
    try:
        result = run(options, reporter)
    except RunError as error:
        _fail(str(error), 1)
    except KeyboardInterrupt:
        _fail("interrupted; anything already recorded was kept", 130)
    except Exception as error:
        _fail(f"unexpected {type(error).__name__}: {error}", 1)
    if result.pricing.stopped is not None:
        # A price-source problem: warn and carry on; the run still succeeds (FR-009).
        reporter.warning(f"price lookups stopped: {result.pricing.stopped.reason}")
    for line in _summary_lines(result):
        typer.echo(line)


def _summary_lines(result: RunResult) -> list[str]:
    """The run's stdout lines (contracts/cli.md for features 001, 002 and 003)."""
    if result.recorded == 0:
        lines = ["No new transactions found."]
    else:
        lines = [f"Recorded {result.recorded} new {_plural(result.recorded, 'transaction')}."]
    if result.imported is not None:
        imported, skipped = result.imported.imported, result.imported.skipped
        lines.append(
            f"Imported {imported} {_plural(imported, 'price')};"
            f" skipped {skipped} {_plural(skipped, 'row')}."
        )
    pricing = result.pricing
    if pricing.priced:
        priced = f"Priced {pricing.priced} {_plural(pricing.priced, 'day')}"
        if pricing.provisional:
            priced += f" ({pricing.provisional} provisional)"
        lines.append(priced + ".")
    if pricing.no_price:
        verb = "has" if pricing.no_price == 1 else "have"
        lines.append(
            f"{pricing.no_price} {_plural(pricing.no_price, 'day')} still {verb} no price;"
            " a later run will try again."
        )
    if pricing.not_refreshed:
        lines.append(
            f"{pricing.not_refreshed} provisional {_plural(pricing.not_refreshed, 'price')}"
            " couldn't be refreshed; a later run will try again."
        )
    if pricing.too_old:
        verb, pronoun = ("is", "it") if pricing.too_old == 1 else ("are", "them")
        lines.append(
            f"{pricing.too_old} {_plural(pricing.too_old, 'day')} {verb} older than the price"
            f" history and can't be looked up; use --import-prices to add {pronoun}."
        )
    if pricing.all_final:
        lines.append("All transactions are valued.")
    if result.exported is not None:
        count = result.exported.transactions
        lines.append(f"Exported {count} {_plural(count, 'transaction')} to {result.exported.path}.")
    return lines


def _plural(count: int, noun: str) -> str:
    return noun if count == 1 else f"{noun}s"


def _fail(message: str, exit_code: int) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(exit_code)


def main() -> None:
    app()
