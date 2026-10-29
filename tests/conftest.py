"""Shared pytest configuration.

Every test runs with HOME pointed at its own temporary directory. Default paths
(the config file and the database) expand ``~`` at call time, so a test that
forgets to pass an explicit path still never touches the user's real data.

Every run also prices after syncing (feature 002). The default price source and
sleep are replaced too, so a test that doesn't pass its own can never reach
CoinGecko or wait in real time.
"""

import importlib
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from monero_income.orchestration.settings import Settings
from tests.fakes.price_source import FakePriceSource

# The package re-exports the run() function under the module's name, so import the module itself.
run_module = importlib.import_module("monero_income.orchestration.run")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture(autouse=True)
def offline_price_source(monkeypatch: pytest.MonkeyPatch) -> None:
    def empty_price_source(settings: Settings) -> FakePriceSource:
        return FakePriceSource()

    def no_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(run_module, "make_price_source", empty_price_source)
    monkeypatch.setattr(run_module, "_sleep", no_sleep)


@pytest.fixture
def local_tz() -> Iterator[Callable[[str], None]]:
    """Set the process's local time zone for one test (research R2).

    Its own MonkeyPatch restores TZ before the final tzset(), so later tests see the
    original zone again.
    """
    with pytest.MonkeyPatch.context() as patch:

        def set_tz(name: str) -> None:
            patch.setenv("TZ", name)
            time.tzset()

        yield set_tz
    time.tzset()
