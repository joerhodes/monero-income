"""Command-line interface: parse options, call run(), print the result.

No behavior lives here (constitution II); everything goes through
``monero_income.orchestration.run``.
"""

from typing import Annotated, NoReturn

import typer

from monero_income.orchestration import CliOptions, RunError, run

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
) -> None:
    options = CliOptions(rpc_url=rpc_url, username=username, db_path=db_path)
    try:
        result = run(options, StderrReporter())
    except RunError as error:
        _fail(str(error), 1)
    except KeyboardInterrupt:
        _fail("interrupted; anything already recorded was kept", 130)
    except Exception as error:
        _fail(f"unexpected {type(error).__name__}: {error}", 1)
    if result.recorded == 0:
        typer.echo("No new transactions found.")
    else:
        noun = "transaction" if result.recorded == 1 else "transactions"
        typer.echo(f"Recorded {result.recorded} new {noun}.")


def _fail(message: str, exit_code: int) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(exit_code)


def main() -> None:
    app()
