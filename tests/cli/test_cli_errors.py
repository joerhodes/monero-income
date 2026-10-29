"""The CLI turns every failure into one 'Error:' line and an exit code; never a traceback."""

import dataclasses
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from typer.testing import CliRunner

from monero_income import cli
from monero_income.orchestration import (
    CliOptions,
    ExportSummary,
    IncomeSummaries,
    Reporter,
    RunError,
    RunResult,
    SummaryError,
    summary_format,
)
from monero_income.orchestration.summary import build_summaries

runner = CliRunner()


def raising(error: BaseException) -> object:
    def fake_run(options: CliOptions, reporter: Reporter) -> RunResult:
        raise error

    return fake_run


@pytest.mark.parametrize(
    ("error", "line", "exit_code"),
    [
        (RunError("x"), "Error: x\n", 1),
        (KeyboardInterrupt(), "Error: interrupted; anything already recorded was kept\n", 130),
        (ValueError("boom"), "Error: unexpected ValueError: boom\n", 1),
    ],
)
def test_failures_are_one_line_with_exit_code(
    monkeypatch: pytest.MonkeyPatch, error: BaseException, line: str, exit_code: int
) -> None:
    monkeypatch.setattr(cli, "run", raising(error))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == exit_code
    assert result.stderr == line
    assert result.stdout == ""
    assert "Traceback" not in result.output


def test_unknown_option_is_a_usage_error() -> None:
    result = runner.invoke(cli.app, ["--password", "x"])

    assert result.exit_code == 2
    assert "Traceback" not in result.output


def test_warning_is_printed_and_the_run_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(options: CliOptions, reporter: Reporter) -> RunResult:
        reporter.warning("config file is readable by other users")
        return RunResult(recorded=2)

    monkeypatch.setattr(cli, "run", fake_run)

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 0
    assert result.stderr == "Warning: config file is readable by other users\n"
    assert result.stdout == "Recorded 2 new transactions.\n"
    assert "Traceback" not in result.output


def test_export_write_failure_prints_only_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    message = (
        "cannot write export /x/reports/xmr_income.csv: Permission denied."
        " Recorded transactions and prices were kept; the previous export was not changed."
    )
    monkeypatch.setattr(cli, "run", raising(RunError(message)))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 1
    assert result.stderr == f"Error: {message}\n"
    assert result.stdout == ""  # no sync or pricing lines on failure


EXPORT_PATH = Path("/x/reports/xmr_income.csv")
EARLIER_LINES = (
    "Recorded 2 new transactions.\nExported 2 transactions to /x/reports/xmr_income.csv.\n"
)


def returning(result: RunResult) -> object:
    def fake_run(options: CliOptions, reporter: Reporter) -> RunResult:
        return result

    return fake_run


def summaries() -> IncomeSummaries:
    return build_summaries([], date(2026, 10, 27), ZoneInfo("America/New_York"))


def test_a_summary_error_from_run_prints_the_earlier_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    message = "cannot show the income summaries: unexpected RuntimeError: boom. The export ..."
    partial = RunResult(recorded=2, exported=ExportSummary(EXPORT_PATH, 2))
    monkeypatch.setattr(cli, "run", raising(SummaryError(message, partial)))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 1
    assert result.stdout == EARLIER_LINES
    assert result.stderr == f"Error: {message}\n"
    assert "Traceback" not in result.output


def test_a_malformed_summary_fails_cleanly_when_rendered(monkeypatch: pytest.MonkeyPatch) -> None:
    good = summaries()
    weekly = dataclasses.replace(good.weekly, periods=good.weekly.periods[:25])
    broken = dataclasses.replace(good, weekly=weekly, transactions=2)
    result_of_run = RunResult(recorded=2, exported=ExportSummary(EXPORT_PATH, 2), summaries=broken)
    monkeypatch.setattr(cli, "run", returning(result_of_run))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 1
    assert result.stdout == EARLIER_LINES
    assert result.stderr.startswith("Error: cannot show the income summaries: unexpected data")
    assert result.stderr.endswith(
        f"The export was written to {EXPORT_PATH}; recorded transactions and prices were kept.\n"
    )
    assert "Traceback" not in result.output


def test_a_renderer_crash_fails_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    def crashing_render(*args: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(summary_format, "render_text", crashing_render)
    result_of_run = RunResult(
        recorded=2, exported=ExportSummary(EXPORT_PATH, 2), summaries=summaries()
    )
    monkeypatch.setattr(cli, "run", returning(result_of_run))

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 1
    assert result.stdout == EARLIER_LINES
    assert result.stderr == (
        "Error: cannot show the income summaries: unexpected RuntimeError: boom."
        f" The export was written to {EXPORT_PATH}; recorded transactions and prices were kept.\n"
    )
    assert "Traceback" not in result.output
