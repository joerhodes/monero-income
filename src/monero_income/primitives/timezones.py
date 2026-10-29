"""Load a time zone by its IANA name from the system's time zone database (research R2)."""

import zoneinfo
from zoneinfo import ZoneInfo

from monero_income.primitives.errors import UnknownTimeZoneError


def load_zone(name: str) -> ZoneInfo:
    """The zone named ``name``, or ``UnknownTimeZoneError(name)``.

    Only names listed by the database are accepted, so a directory, a path, or a name in the
    wrong case is rejected on every platform, even on a case-insensitive file system.
    """
    if name not in zoneinfo.available_timezones():
        raise UnknownTimeZoneError(name)
    try:
        return ZoneInfo(name)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError) as error:
        raise UnknownTimeZoneError(name) from error
