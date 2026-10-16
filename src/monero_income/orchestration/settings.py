"""Resolve run settings from CLI options, the config file, and defaults. Pure.

Precedence per key: command-line option, then config file, then default. The
password comes from the config file only. Messages never include the password.
"""

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from monero_income.orchestration.errors import RunError
from monero_income.primitives.config_file import RawConfig

DEFAULT_RPC_URL = "http://127.0.0.1:18088/json_rpc"
DEFAULT_DB_PATH = "~/.local/share/monero-income/xmr.db"

# Keys this version understands, all strings. Later features add their keys here.
KNOWN_KEYS = ("rpc_url", "username", "password", "db_path")


@dataclass(frozen=True)
class CliOptions:
    """Values given on the command line; ``None`` means not given. No password, by design."""

    rpc_url: str | None = None
    username: str | None = None
    db_path: str | None = None


@dataclass(frozen=True)
class Settings:
    rpc_url: str
    username: str | None
    password: str | None = field(repr=False)
    db_path: Path


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

    file_values = {key: _file_string(values, key, config_path) for key in KNOWN_KEYS}

    rpc_url = _pick(options.rpc_url, file_values["rpc_url"]) or DEFAULT_RPC_URL
    _check_rpc_url(rpc_url, config_path)

    username = _pick(options.username, file_values["username"])
    if username == "":
        raise RunError("invalid username: must not be empty")

    password = file_values["password"]
    if password is not None and username is None:
        raise RunError(f"password is set in {config_path} but username is not")

    db_path = _pick(options.db_path, file_values["db_path"]) or DEFAULT_DB_PATH
    if not db_path.strip():
        raise RunError("invalid db_path: must not be empty")

    settings = Settings(
        rpc_url=rpc_url,
        username=username,
        password=password,
        db_path=Path(db_path).expanduser(),
    )
    return settings, warnings


def _pick(option: str | None, from_file: str | None) -> str | None:
    return option if option is not None else from_file


def _file_string(values: dict[str, object], key: str, config_path: Path) -> str | None:
    value = values.get(key)
    if value is None or isinstance(value, str):
        return value
    raise RunError(f"invalid {key} in {config_path}: expected a string")


def _check_rpc_url(url: str, config_path: Path) -> None:
    # Never echo the URL: it may carry credentials.
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise RunError("invalid rpc_url: must start with http:// or https://")
    if "@" in parts.netloc:
        raise RunError(
            "invalid rpc_url: must not contain a username or password; "
            f"set username and password in {config_path}"
        )
    if not parts.hostname:
        raise RunError("invalid rpc_url: missing host")
