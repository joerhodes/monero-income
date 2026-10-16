"""US3 / FR-015: every failure is a RunError with its category phrase; never the password."""

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from monero_income.orchestration import CliOptions, RunError, run
from monero_income.orchestration.settings import Settings
from monero_income.primitives.errors import (
    WalletLoginError,
    WalletResponseError,
    WalletRpcError,
    WalletUnreachableError,
)
from monero_income.primitives.wallet_rpc import WalletRpc
from tests.fakes.reporter import ListReporter
from tests.fakes.wallet import FakeWalletRpc, entry

PASSWORD = "pw-Zq9!secret"
SQLITE_INTEGER_MAX = 9_223_372_036_854_775_807


def write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text)
    path.chmod(0o600)
    return path


def login_config(tmp_path: Path) -> Path:
    return write_config(tmp_path, f'username = "monero"\npassword = "{PASSWORD}"\n')


def failing_wallet(failure: BaseException) -> FakeWalletRpc:
    return FakeWalletRpc(height=100, fail_on_call=1, failure=failure)


def run_error(
    tmp_path: Path,
    *,
    options: CliOptions | None = None,
    config_path: Path | None = None,
    wallet_factory: Callable[[Settings], WalletRpc] | None = None,
) -> str:
    with pytest.raises(RunError) as excinfo:
        run(
            options or CliOptions(db_path=str(tmp_path / "xmr.db")),
            ListReporter(),
            config_path=config_path or login_config(tmp_path),
            wallet_factory=wallet_factory or (lambda settings: FakeWalletRpc(height=10)),
        )
    message = str(excinfo.value)
    assert PASSWORD not in message
    assert "transfer" not in message.lower()
    return message


@pytest.mark.parametrize(
    ("failure", "phrase"),
    [
        (WalletUnreachableError("connection refused"), "cannot reach the wallet at"),
        (WalletLoginError("the wallet rejected the login"), "rejected the login"),
        (WalletRpcError(-13, "No wallet file"), "the wallet returned an error"),
        (WalletResponseError("the response is not JSON"), "unexpected response from the wallet"),
    ],
)
def test_wallet_failures(tmp_path: Path, failure: BaseException, phrase: str) -> None:
    message = run_error(tmp_path, wallet_factory=lambda settings: failing_wallet(failure))

    assert phrase in message


def test_unreachable_names_the_wallet_address(tmp_path: Path) -> None:
    message = run_error(
        tmp_path,
        wallet_factory=lambda settings: failing_wallet(WalletUnreachableError("refused")),
    )

    assert "http://127.0.0.1:18088/json_rpc" in message


def test_unreadable_database_is_left_unchanged(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    db_path.write_bytes(b"junk")

    message = run_error(tmp_path, options=CliOptions(db_path=str(db_path)))

    assert "cannot read database" in message
    assert db_path.read_bytes() == b"junk"


def test_write_failure(tmp_path: Path) -> None:
    wallet = FakeWalletRpc(
        entries=[entry("too-big", height=5, amount=SQLITE_INTEGER_MAX + 1)], height=10
    )

    message = run_error(tmp_path, wallet_factory=lambda settings: wallet)

    assert "cannot write to database" in message


def test_newer_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "xmr.db"
    raw = sqlite3.connect(db_path)
    raw.execute("PRAGMA user_version = 2")
    raw.commit()
    raw.close()

    message = run_error(tmp_path, options=CliOptions(db_path=str(db_path)))

    assert "newer version of monero-income" in message


def test_invalid_config_file(tmp_path: Path) -> None:
    config = write_config(tmp_path, f'password = "{PASSWORD}"\nusername =\n')

    assert "cannot read config file" in run_error(tmp_path, config_path=config)


def test_password_without_username_never_contacts_the_wallet(tmp_path: Path) -> None:
    config = write_config(tmp_path, f'password = "{PASSWORD}"\n')
    called: list[Settings] = []

    def factory(settings: Settings) -> WalletRpc:
        called.append(settings)
        return FakeWalletRpc()

    assert "password is set" in run_error(tmp_path, config_path=config, wallet_factory=factory)
    assert called == []


def test_invalid_rpc_url(tmp_path: Path) -> None:
    message = run_error(
        tmp_path, options=CliOptions(rpc_url="ftp://wallet", db_path=str(tmp_path / "x.db"))
    )

    assert "invalid rpc_url" in message
