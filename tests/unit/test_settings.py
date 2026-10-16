import dataclasses
from pathlib import Path

import pytest

from monero_income.orchestration.errors import RunError
from monero_income.orchestration.settings import (
    CliOptions,
    Settings,
    default_config_path,
    is_readable_by_others,
    resolve_settings,
)
from monero_income.primitives.config_file import RawConfig

CONFIG = Path("/home/u/.config/monero-income/config.toml")
PASSWORD = "pw-Zq9!secret"
PRIVATE = 0o100600
SHARED = 0o100644


def raw(mode: int = PRIVATE, **values: object) -> RawConfig:
    return RawConfig(values=values, mode=mode)


def resolve(options: CliOptions | None = None, file: RawConfig | None = None) -> Settings:
    settings, _ = resolve_settings(options or CliOptions(), file, CONFIG)
    return settings


def test_defaults_apply_without_options_or_file(isolated_home: Path) -> None:
    settings, warnings = resolve_settings(CliOptions(), None, CONFIG)

    assert settings == Settings(
        rpc_url="http://127.0.0.1:18088/json_rpc",
        username=None,
        password=None,
        db_path=isolated_home / ".local/share/monero-income/xmr.db",
    )
    assert warnings == []


def test_default_config_path_expands_home_at_call_time(isolated_home: Path) -> None:
    assert default_config_path() == isolated_home / ".config/monero-income/config.toml"


def test_file_overrides_defaults_and_options_override_file(isolated_home: Path) -> None:
    file = raw(rpc_url="http://10.0.0.5:18088/json_rpc", username="file-user", db_path="~/f.db")

    from_file = resolve(file=file)
    assert from_file.rpc_url == "http://10.0.0.5:18088/json_rpc"
    assert from_file.username == "file-user"
    assert from_file.db_path == isolated_home / "f.db"

    options = CliOptions(
        rpc_url="https://wallet.lan/json_rpc", username="cli-user", db_path="/tmp/cli.db"
    )
    from_cli = resolve(options, file)
    assert from_cli.rpc_url == "https://wallet.lan/json_rpc"
    assert from_cli.username == "cli-user"
    assert from_cli.db_path == Path("/tmp/cli.db")


@pytest.mark.parametrize(
    "url",
    [
        "ftp://127.0.0.1/json_rpc",
        "127.0.0.1:18088/json_rpc",
        "http:///json_rpc",
        "http://u:p@127.0.0.1:18088/json_rpc",
        "http://u@127.0.0.1:18088/json_rpc",
    ],
)
def test_invalid_rpc_url_is_rejected(url: str) -> None:
    with pytest.raises(RunError, match="invalid rpc_url"):
        resolve(CliOptions(rpc_url=url))


def test_rpc_url_with_credentials_is_not_echoed() -> None:
    with pytest.raises(RunError) as excinfo:
        resolve(CliOptions(rpc_url=f"http://monero:{PASSWORD}@127.0.0.1:18088/json_rpc"))

    assert PASSWORD not in str(excinfo.value)


def test_empty_username_is_invalid() -> None:
    with pytest.raises(RunError, match="invalid username"):
        resolve(CliOptions(username=""))


def test_password_without_username_is_an_error() -> None:
    with pytest.raises(RunError) as excinfo:
        resolve(file=raw(password=PASSWORD))

    assert str(excinfo.value) == f"password is set in {CONFIG} but username is not"


def test_password_comes_from_the_file_only() -> None:
    assert "password" not in {field.name for field in dataclasses.fields(CliOptions)}

    settings = resolve(CliOptions(username="cli-user"), raw(password=PASSWORD))
    assert settings.password == PASSWORD


def test_username_without_password_is_allowed() -> None:
    settings = resolve(file=raw(username="monero"))

    assert settings.username == "monero"
    assert settings.password is None


def test_unknown_key_is_a_warning_naming_it() -> None:
    _, warnings = resolve_settings(CliOptions(), raw(price_api="x"), CONFIG)

    assert len(warnings) == 1
    assert "price_api" in warnings[0]


@pytest.mark.parametrize("key", ["rpc_url", "username", "password", "db_path"])
def test_known_key_with_wrong_type_is_invalid(key: str) -> None:
    with pytest.raises(RunError, match=f"invalid {key}"):
        resolve(file=raw(**{key: 18088}))


def test_permissions() -> None:
    assert is_readable_by_others(SHARED)
    assert not is_readable_by_others(PRIVATE)


def test_config_readable_by_others_is_a_warning() -> None:
    _, warnings = resolve_settings(CliOptions(), raw(mode=SHARED), CONFIG)

    assert warnings == [f"config file {CONFIG} is readable by other users; run chmod 600 on it"]


def test_password_never_appears_in_errors_warnings_or_repr() -> None:
    file = raw(mode=SHARED, password=PASSWORD, username="monero", extra=PASSWORD)

    settings, warnings = resolve_settings(CliOptions(), file, CONFIG)

    assert all(PASSWORD not in warning for warning in warnings)
    assert PASSWORD not in repr(settings)
    with pytest.raises(RunError) as excinfo:
        resolve_settings(CliOptions(rpc_url="nope"), file, CONFIG)
    assert PASSWORD not in str(excinfo.value)
