import dataclasses
from decimal import Decimal
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
        reports_path=isolated_home / "reports",
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


@pytest.mark.parametrize("key", ["rpc_url", "username", "password", "db_path", "reports_path"])
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


# --- feature 002: price source keys ---------------------------------------------------------

API_KEY = "CG-Zq9!distinctive-key"


def test_price_source_defaults() -> None:
    settings = resolve()

    assert settings.coingecko_url == "https://api.coingecko.com/api/v3"
    assert settings.coin_id == "monero"
    assert settings.api_key is None
    assert settings.api_key_type is None
    assert settings.min_request_delay is None
    assert settings.import_prices is None


def test_pro_key_type_defaults_to_the_pro_host() -> None:
    settings = resolve(file=raw(coingecko_api_key=API_KEY, coingecko_api_key_type="pro"))

    assert settings.coingecko_url == "https://pro-api.coingecko.com/api/v3"
    assert settings.api_key == API_KEY
    assert settings.api_key_type == "pro"


def test_explicit_coingecko_url_wins_over_the_key_type_default() -> None:
    settings = resolve(
        file=raw(
            coingecko_api_key=API_KEY,
            coingecko_api_key_type="pro",
            coingecko_url="https://proxy.lan/api/v3",
        )
    )

    assert settings.coingecko_url == "https://proxy.lan/api/v3"


def test_key_and_type_on_the_command_line_override_the_file() -> None:
    options = CliOptions(coingecko_api_key="CG-cli", coingecko_api_key_type="demo")
    file = raw(coingecko_api_key=API_KEY, coingecko_api_key_type="pro")

    settings = resolve(options, file)

    assert settings.api_key == "CG-cli"
    assert settings.api_key_type == "demo"
    assert settings.coingecko_url == "https://api.coingecko.com/api/v3"


def test_key_without_a_type_is_an_error() -> None:
    with pytest.raises(RunError) as excinfo:
        resolve(file=raw(coingecko_api_key=API_KEY))

    assert "invalid coingecko_api_key_type: required when coingecko_api_key is set" in str(
        excinfo.value
    )
    assert API_KEY not in str(excinfo.value)


@pytest.mark.parametrize("key_type", ["paid", "DEMO", ""])
def test_unknown_key_type_is_invalid(key_type: str) -> None:
    with pytest.raises(RunError, match="invalid coingecko_api_key_type"):
        resolve(CliOptions(coingecko_api_key=API_KEY, coingecko_api_key_type=key_type))


def test_empty_key_is_invalid() -> None:
    with pytest.raises(RunError, match="invalid coingecko_api_key"):
        resolve(CliOptions(coingecko_api_key="", coingecko_api_key_type="demo"))


def test_key_type_without_a_key_is_a_warning() -> None:
    settings, warnings = resolve_settings(CliOptions(), raw(coingecko_api_key_type="demo"), CONFIG)

    assert settings.api_key_type is None
    assert any("coingecko_api_key_type" in warning for warning in warnings)


@pytest.mark.parametrize(
    "url",
    ["ftp://api.coingecko.com/api/v3", "https:///api/v3", f"https://u:{API_KEY}@host/api/v3"],
)
def test_invalid_coingecko_url(url: str) -> None:
    with pytest.raises(RunError, match="invalid coingecko_url") as excinfo:
        resolve(file=raw(coingecko_url=url))

    assert API_KEY not in str(excinfo.value)


@pytest.mark.parametrize("coin_id", ["", "Monero", "mon ero", "monero/../x"])
def test_invalid_coin_id(coin_id: str) -> None:
    with pytest.raises(RunError, match="invalid coin_id"):
        resolve(file=raw(coin_id=coin_id))


@pytest.mark.parametrize(
    ("value", "expected"),
    [(2, Decimal("2")), (2.5, Decimal("2.5")), (0, Decimal("0")), (60, Decimal("60"))],
)
def test_min_request_delay_accepts_numbers(value: object, expected: Decimal) -> None:
    assert resolve(file=raw(min_request_delay=value)).min_request_delay == expected


@pytest.mark.parametrize("value", ["2.5", -1, 60.5, True])
def test_min_request_delay_rejects_non_numbers_and_out_of_range(value: object) -> None:
    with pytest.raises(RunError, match="invalid min_request_delay"):
        resolve(file=raw(min_request_delay=value))


def test_import_prices_is_passed_through_with_home_expanded(isolated_home: Path) -> None:
    settings = resolve(CliOptions(import_prices="~/prices.csv"))

    assert settings.import_prices == isolated_home / "prices.csv"


def test_api_key_never_appears_in_repr_warnings_or_errors() -> None:
    file = raw(
        mode=SHARED,
        coingecko_api_key=API_KEY,
        coingecko_api_key_type="demo",
        unknown=API_KEY,
    )

    settings, warnings = resolve_settings(CliOptions(), file, CONFIG)

    assert API_KEY not in repr(settings)
    assert all(API_KEY not in warning for warning in warnings)
    with pytest.raises(RunError) as excinfo:
        resolve_settings(CliOptions(rpc_url="nope"), file, CONFIG)
    assert API_KEY not in str(excinfo.value)


def test_reports_path_defaults_to_reports_in_home(isolated_home: Path) -> None:
    assert resolve().reports_path == isolated_home / "reports"


def test_reports_path_from_the_file_with_home_expanded(isolated_home: Path) -> None:
    assert resolve(file=raw(reports_path="/srv/reports")).reports_path == Path("/srv/reports")
    assert resolve(file=raw(reports_path="~/audit")).reports_path == isolated_home / "audit"


def test_reports_path_option_overrides_the_file(isolated_home: Path) -> None:
    settings = resolve(CliOptions(reports_path="~/cli"), raw(reports_path="/srv/reports"))

    assert settings.reports_path == isolated_home / "cli"


@pytest.mark.parametrize("value", ["", "  "])
def test_empty_reports_path_is_invalid_not_the_default(value: str) -> None:
    for options, file in ((CliOptions(reports_path=value), None), (None, raw(reports_path=value))):
        with pytest.raises(RunError) as excinfo:
            resolve(options, file)
        assert str(excinfo.value) == "invalid reports_path: must not be empty"


def test_reports_path_with_wrong_type_names_the_config_file() -> None:
    with pytest.raises(RunError) as excinfo:
        resolve(file=raw(reports_path=5))

    assert str(excinfo.value) == f"invalid reports_path in {CONFIG}: expected a string"


def test_reports_path_is_a_known_key() -> None:
    _, warnings = resolve_settings(CliOptions(), raw(reports_path="/srv/reports"), CONFIG)

    assert warnings == []


# --- feature 004: timezone (contracts/config.md) ---------------------------------------------


def test_timezone_defaults_to_none() -> None:
    assert resolve().timezone is None


def test_timezone_from_the_file() -> None:
    assert resolve(file=raw(timezone="America/New_York")).timezone == "America/New_York"


def test_timezone_option_overrides_the_file() -> None:
    settings = resolve(CliOptions(timezone="UTC"), raw(timezone="America/New_York"))
    assert settings.timezone == "UTC"


@pytest.mark.parametrize("value", ["", "  "])
def test_empty_timezone_is_invalid_not_the_default(value: str) -> None:
    for options, file in ((CliOptions(timezone=value), None), (None, raw(timezone=value))):
        with pytest.raises(RunError) as excinfo:
            resolve(options, file)
        assert str(excinfo.value) == "invalid timezone: must not be empty"


def test_timezone_with_wrong_type_names_the_config_file() -> None:
    with pytest.raises(RunError) as excinfo:
        resolve(file=raw(timezone=5))

    assert str(excinfo.value) == f"invalid timezone in {CONFIG}: expected a string"


def test_timezone_is_a_known_key() -> None:
    _, warnings = resolve_settings(CliOptions(), raw(timezone="UTC"), CONFIG)

    assert warnings == []
