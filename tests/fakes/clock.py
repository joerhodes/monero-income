"""A settable clock and a sleep that records instead of waiting."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass
class FakeClock:
    """Callable as ``clock()``; returns ``now``, an aware UTC datetime."""

    now: datetime = field(default_factory=lambda: datetime(2026, 10, 17, 12, tzinfo=UTC))

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@dataclass
class RecordingSleep:
    """Records each requested sleep; advances ``clock`` by it when one is linked."""

    clock: FakeClock | None = None
    calls: list[float] = field(default_factory=list)

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        if self.clock is not None:
            self.clock.advance(seconds)
