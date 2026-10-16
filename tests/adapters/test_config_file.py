import os
import stat
from pathlib import Path

import pytest

from monero_income.primitives.config_file import RawConfig, read_config
from monero_income.primitives.errors import ConfigFileError

PASSWORD = "pw-Zq9!secret"


def test_missing_file_is_none(tmp_path: Path) -> None:
    assert read_config(tmp_path / "config.toml") is None


def test_valid_toml_returns_values_and_mode(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('rpc_url = "http://127.0.0.1:18088/json_rpc"\nusername = "monero"\n')
    path.chmod(0o600)

    raw = read_config(path)

    assert raw == RawConfig(
        values={"rpc_url": "http://127.0.0.1:18088/json_rpc", "username": "monero"},
        mode=path.stat().st_mode,
    )
    assert stat.S_IMODE(raw.mode) == 0o600


def test_invalid_toml_names_path_and_location_but_not_contents(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(f'password = "{PASSWORD}"\nusername = \n')

    with pytest.raises(ConfigFileError) as excinfo:
        read_config(path)

    message = str(excinfo.value)
    assert str(path) in message
    assert "line 2" in message
    assert PASSWORD not in message


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
def test_unreadable_file_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('username = "monero"\n')
    path.chmod(0o000)
    try:
        with pytest.raises(ConfigFileError) as excinfo:
            read_config(path)
        assert str(path) in str(excinfo.value)
    finally:
        path.chmod(0o600)
