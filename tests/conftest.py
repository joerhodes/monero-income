"""Shared pytest configuration.

Every test runs with HOME pointed at its own temporary directory. Default paths
(the config file and the database) expand ``~`` at call time, so a test that
forgets to pass an explicit path still never touches the user's real data.
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home
