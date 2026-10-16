"""Read the TOML config file. Only reads; validation is orchestration's job."""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from monero_income.primitives.errors import ConfigFileError


@dataclass(frozen=True)
class RawConfig:
    values: Mapping[str, object]
    mode: int  # st_mode, for the permissions warning


def read_config(path: Path) -> RawConfig | None:
    """Return the file's values and mode, or ``None`` if the file doesn't exist.

    Error messages name the file and, for syntax errors, the location. They never
    quote the file's contents, which may include the wallet password.
    """
    try:
        data = path.read_bytes()
        mode = path.stat().st_mode
    except FileNotFoundError:
        return None
    except OSError as error:
        raise ConfigFileError(f"{path}: {error.strerror or type(error).__name__}") from error
    try:
        values = tomllib.loads(data.decode("utf-8"))
    except UnicodeDecodeError as error:
        raise ConfigFileError(f"{path}: not valid UTF-8") from error
    except tomllib.TOMLDecodeError as error:
        # str(error) is the parser's message and location, e.g. "Invalid value (at line 2,
        # column 12)"; it doesn't include the document.
        raise ConfigFileError(f"{path}: {error}") from error
    return RawConfig(values=values, mode=mode)
