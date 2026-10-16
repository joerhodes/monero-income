"""Command-line interface: parse options, call run(), print the result.

No behavior lives here (constitution II); everything goes through
``monero_income.orchestration.run``.
"""

from typing import Annotated

import typer

from monero_income.orchestration import CliOptions, run

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
    result = run(options, StderrReporter())
    noun = "transaction" if result.recorded == 1 else "transactions"
    typer.echo(f"Recorded {result.recorded} new {noun}.")


def main() -> None:
    app()
