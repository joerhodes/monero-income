"""In-memory stand-in for the price source."""

from dataclasses import dataclass, field
from datetime import date

from monero_income.primitives.price_parse import NoPrice, PriceAnswer
from monero_income.primitives.price_source import PriceSource

Answer = PriceAnswer | BaseException
NO_PRICE = NoPrice("no price for this date")


@dataclass
class FakePriceSource:
    """Answers ``daily_price`` from a map of day → answer, exception, or list of them.

    An exception is raised once and then removed, unless ``repeat`` is True. A list
    is used up one entry per call, in order, then the day answers ``NoPrice``.
    Unmapped days answer ``NoPrice``. Every requested day is recorded, in order, in
    ``requests``.
    """

    answers: dict[date, Answer | list[Answer]] = field(default_factory=dict)
    repeat: bool = False
    requests: list[date] = field(default_factory=list)

    def daily_price(self, day: date) -> PriceAnswer:
        self.requests.append(day)
        entry = self.answers.get(day, NO_PRICE)
        if isinstance(entry, list):
            answer = entry.pop(0) if entry else NO_PRICE
        else:
            answer = entry
            if isinstance(answer, BaseException) and not self.repeat:
                del self.answers[day]
        if isinstance(answer, BaseException):
            raise answer
        return answer


def _satisfies_protocol(fake: FakePriceSource) -> PriceSource:
    return fake  # mypy checks FakePriceSource against the PriceSource Protocol here
