"""Resolve run settings from CLI options, the config file, and defaults. Pure.

Precedence per key: command-line option, then config file, then default. The
password comes from the config file only. Messages never include the password or
the price source API key.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from monero_income.orchestration.errors import RunError
from monero_income.primitives.config_file import RawConfig

DEFAULT_RPC_URL = "http://127.0.0.1:18088/json_rpc"
DEFAULT_DB_PATH = "~/.local/share/monero-income/xmr.db"
DEFAULT_REPORTS_PATH = "~/reports"
DEFAULT_COINGECKO_URL = "https://api.coingecko.com/api/v3"
DEFAULT_COINGECKO_PRO_URL = "https://pro-api.coingecko.com/api/v3"
DEFAULT_COIN_ID = "monero"
MAX_REQUEST_DELAY = Decimal(60)

# String keys this version understands. Later features add their keys here.
STRING_KEYS = (
    "rpc_url",
    "username",
    "password",
    "db_path",
    "coingecko_url",
    "coin_id",
    "coingecko_api_key",
    "coingecko_api_key_type",
    "reports_path",
    "timezone",
)
NUMBER_KEYS = ("min_request_delay",)
KNOWN_KEYS = STRING_KEYS + NUMBER_KEYS

_COIN_ID = re.compile(r"[a-z0-9-]+")

KeyType = Literal["demo", "pro"]


@dataclass(frozen=True)
class CliOptions:
    """Values given on the command line; ``None`` means not given. No password, by design."""

    rpc_url: str | None = None
    username: str | None = None
    db_path: str | None = None
    import_prices: str | None = None
    coingecko_api_key: str | None = None
    coingecko_api_key_type: str | None = None
    reports_path: str | None = None
    timezone: str | None = None


@dataclass(frozen=True)
class Settings:
    rpc_url: str
    username: str | None
    password: str | None = field(repr=False)
    db_path: Path
    coingecko_url: str = DEFAULT_COINGECKO_URL
    coin_id: str = DEFAULT_COIN_ID
    api_key: str | None = field(default=None, repr=False)
    api_key_type: KeyType | None = None
    min_request_delay: Decimal | None = None  # seconds; None means the default for the key
    import_prices: Path | None = None
    reports_path: Path = Path(DEFAULT_REPORTS_PATH)  # placeholder; resolve_settings sets it
    timezone: str | None = None  # None means the machine's local zone; loaded by run()


def default_config_path() -> Path:
    """The config file location, with ``~`` expanded now (not at import time)."""
    return Path("~/.config/monero-income/config.toml").expanduser()


def is_readable_by_others(mode: int) -> bool:
    return bool(mode & 0o004)


def resolve_settings(
    options: CliOptions, raw: RawConfig | None, config_path: Path
) -> tuple[Settings, list[str]]:
    """Return the resolved settings and any warnings, or raise ``RunError``."""
    values = dict(raw.values) if raw is not None else {}
    warnings = [
        f"config file {config_path}: unknown key '{key}' ignored"
        for key in values
        if key not in KNOWN_KEYS
    ]
    if raw is not None and is_readable_by_others(raw.mode):
        warnings.append(
            f"config file {config_path} is readable by other users; run chmod 600 on it"
        )

    file_values = {key: _file_string(values, key, config_path) for key in STRING_KEYS}

    rpc_url = _pick(options.rpc_url, file_values["rpc_url"]) or DEFAULT_RPC_URL
    _check_url("rpc_url", rpc_url, f"set username and password in {config_path}")

    username = _pick(options.username, file_values["username"])
    if username == "":
        raise RunError("invalid username: must not be empty")

    password = file_values["password"]
    if password is not None and username is None:
        raise RunError(f"password is set in {config_path} but username is not")

    db_path = _pick(options.db_path, file_values["db_path"]) or DEFAULT_DB_PATH
    if not db_path.strip():
        raise RunError("invalid db_path: must not be empty")

    # Check for empty before applying the default, so "" is an error and not the default.
    picked_reports_path = _pick(options.reports_path, file_values["reports_path"])
    if picked_reports_path is not None and not picked_reports_path.strip():
        raise RunError("invalid reports_path: must not be empty")
    reports_path = picked_reports_path if picked_reports_path is not None else DEFAULT_REPORTS_PATH

    # Same check as reports_path; the zone itself is loaded by run(), so this stays pure.
    timezone = _pick(options.timezone, file_values["timezone"])
    if timezone is not None and not timezone.strip():
        raise RunError("invalid timezone: must not be empty")

    api_key = _pick(options.coingecko_api_key, file_values["coingecko_api_key"])
    key_type_text = _pick(options.coingecko_api_key_type, file_values["coingecko_api_key_type"])
    api_key_type: KeyType | None = None
    if api_key is not None:
        if api_key == "":
            raise RunError("invalid coingecko_api_key: must not be empty")
        if key_type_text is None:
            raise RunError("invalid coingecko_api_key_type: required when coingecko_api_key is set")
        api_key_type = _key_type(key_type_text)
    elif key_type_text is not None:
        warnings.append("coingecko_api_key_type is set but coingecko_api_key is not; ignored")

    default_url = DEFAULT_COINGECKO_PRO_URL if api_key_type == "pro" else DEFAULT_COINGECKO_URL
    coingecko_url = file_values["coingecko_url"] or default_url
    _check_url("coingecko_url", coingecko_url, "put the API key in coingecko_api_key")

    coin_id = file_values["coin_id"]
    if coin_id is None:
        coin_id = DEFAULT_COIN_ID
    elif not _COIN_ID.fullmatch(coin_id):
        raise RunError("invalid coin_id: use lowercase letters, digits and hyphens")

    import_prices = None
    if options.import_prices is not None:
        if not options.import_prices.strip():
            raise RunError("invalid --import-prices: must not be empty")
        import_prices = Path(options.import_prices).expanduser()

    settings = Settings(
        rpc_url=rpc_url,
        username=username,
        password=password,
        db_path=Path(db_path).expanduser(),
        coingecko_url=coingecko_url,
        coin_id=coin_id,
        api_key=api_key,
        api_key_type=api_key_type,
        min_request_delay=_request_delay(values, config_path),
        import_prices=import_prices,
        reports_path=Path(reports_path).expanduser(),
        timezone=timezone,
    )
    return settings, warnings


def _pick(option: str | None, from_file: str | None) -> str | None:
    return option if option is not None else from_file


def _file_string(values: dict[str, object], key: str, config_path: Path) -> str | None:
    value = values.get(key)
    if value is None or isinstance(value, str):
        return value
    raise RunError(f"invalid {key} in {config_path}: expected a string")


def _check_url(key: str, url: str, credentials_hint: str) -> None:
    # Never echo the URL: it may carry credentials.
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise RunError(f"invalid {key}: must start with http:// or https://")
    if "@" in parts.netloc:
        raise RunError(
            f"invalid {key}: must not contain a username or password; {credentials_hint}"
        )
    if not parts.hostname:
        raise RunError(f"invalid {key}: missing host")


def _key_type(text: str) -> KeyType:
    if text == "demo":
        return "demo"
    if text == "pro":
        return "pro"
    raise RunError("invalid coingecko_api_key_type: must be demo or pro")


def _request_delay(values: dict[str, object], config_path: Path) -> Decimal | None:
    value = values.get("min_request_delay")
    if value is None:
        return None
    # bool is a subclass of int; a delay is a duration, not money, so float input is fine.
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RunError(f"invalid min_request_delay in {config_path}: expected a number")
    delay = Decimal(str(value))
    if not Decimal(0) <= delay <= MAX_REQUEST_DELAY:
        raise RunError("invalid min_request_delay: must be between 0 and 60 seconds")
    return delay
