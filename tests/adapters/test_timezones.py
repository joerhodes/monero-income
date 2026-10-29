"""load_zone: a name from the system's time zone database, or UnknownTimeZoneError (R2)."""

import zoneinfo
from zoneinfo import ZoneInfo

import pytest

from monero_income.primitives.errors import UnknownTimeZoneError
from monero_income.primitives.timezones import load_zone


@pytest.mark.parametrize("name", ["America/New_York", "UTC"])
def test_a_known_name_gives_its_zone(name: str) -> None:
    zone = load_zone(name)

    assert isinstance(zone, ZoneInfo)
    assert zone.key == name


@pytest.mark.parametrize(
    "name",
    [
        "Mars/Olympus_Mons",
        "America",  # a directory in the database, not a zone
        "america/new_york",  # wrong case: rejected even on case-insensitive file systems
        "../etc/passwd",
        "/etc/passwd",
    ],
)
def test_an_unknown_name_is_rejected_with_the_name(name: str) -> None:
    with pytest.raises(UnknownTimeZoneError) as excinfo:
        load_zone(name)

    assert str(excinfo.value) == name


def test_a_listed_name_that_fails_to_load_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # The listing and the zone files can disagree, e.g. a damaged database.
    monkeypatch.setattr(zoneinfo, "available_timezones", lambda: {"Gone/Zone"})

    with pytest.raises(UnknownTimeZoneError) as excinfo:
        load_zone("Gone/Zone")

    assert str(excinfo.value) == "Gone/Zone"
