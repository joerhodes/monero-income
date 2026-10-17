"""In-memory stand-in for the price source."""

from dataclasses import dataclass, field
from datetime import date

from monero_income.primitives.price_parse import NoPrice, PriceAnswer


@dataclass
class FakePriceSource:
    """Answers ``daily_price`` from a map of day → answer or exception.

    An exception is raised once and then removed, unless ``repeat`` is True. Unmapped
    days answer ``NoPrice``. Every requested day is recorded, in order, in ``requests``.
    """

    answers: dict[date, PriceAnswer | BaseException] = field(default_factory=dict)
    repeat: bool = False
    requests: list[date] = field(default_factory=list)

    def daily_price(self, day: date) -> PriceAnswer:
        self.requests.append(day)
        answer = self.answers.get(day, NoPrice("no price for this date"))
        if isinstance(answer, BaseException):
            if not self.repeat:
                del self.answers[day]
            raise answer
        return answer


# The mypy check against the PriceSource Protocol is added with the Protocol itself (T018).
