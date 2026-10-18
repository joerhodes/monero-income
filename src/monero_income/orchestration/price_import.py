"""The optional price import step (US4). For now, only its result type."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportSummary:
    imported: int
    skipped: int
