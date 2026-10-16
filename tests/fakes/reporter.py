"""A Reporter that collects warnings instead of printing them."""

from dataclasses import dataclass, field


@dataclass
class ListReporter:
    warnings: list[str] = field(default_factory=list)

    def warning(self, message: str) -> None:
        self.warnings.append(message)
