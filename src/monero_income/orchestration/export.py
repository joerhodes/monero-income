"""The export step: write every recorded transaction to the reports directory's CSV file."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExportSummary:
    path: Path  # absolute path of the export written
    transactions: int  # data rows written
