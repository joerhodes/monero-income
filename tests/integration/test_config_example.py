"""config.toml.example stays in step with the README and with the settings the tool reads.

The example is the README's Configure block, copied exactly. These tests fail when either
changes without the other, when a config key is added without being documented, when a
"default" comment stops matching the code's default, or when the example stops loading.
"""

import re
import shutil
import tomllib
from pathlib import Path

from monero_income.orchestration.settings import (
    DEFAULT_COIN_ID,
    DEFAULT_COINGECKO_URL,
    DEFAULT_DB_PATH,
    DEFAULT_REPORTS_PATH,
    DEFAULT_RPC_URL,
    KNOWN_KEYS,
    CliOptions,
    resolve_settings,
)
from monero_income.primitives.config_file import read_config
from monero_income.primitives.timezones import load_zone

ROOT = Path(__file__).parent.parent.parent
EXAMPLE = ROOT / "config.toml.example"
README = ROOT / "README.md"

# The values the example's "# default ..." comments claim are the defaults.
DEFAULTS = {
    "rpc_url": DEFAULT_RPC_URL,
    "db_path": DEFAULT_DB_PATH,
    "reports_path": DEFAULT_REPORTS_PATH,
    "coingecko_url": DEFAULT_COINGECKO_URL,
    "coin_id": DEFAULT_COIN_ID,
}


def readme_config_block() -> str:
    """The ```toml block in the README's Configure section."""
    section = README.read_text().split("### Configure", 1)[1]
    match = re.search(r"```toml\n(.*?)```", section, re.DOTALL)
    assert match is not None, "README's Configure section has no ```toml block"
    return match.group(1)


def test_the_example_is_the_readme_configure_block() -> None:
    assert EXAMPLE.read_text() == readme_config_block()


def test_the_example_shows_every_config_key() -> None:
    values = tomllib.loads(EXAMPLE.read_text())

    assert sorted(values) == sorted(KNOWN_KEYS)


def test_default_comments_match_the_code() -> None:
    values = tomllib.loads(EXAMPLE.read_text())
    marked = [
        line.split("=", 1)[0].strip()
        for line in EXAMPLE.read_text().splitlines()
        if re.search(r"#\s*default\b", line)
    ]

    assert sorted(marked) == sorted(DEFAULTS)
    assert {key: values[key] for key in marked} == DEFAULTS


def test_the_example_loads_and_validates(tmp_path: Path, isolated_home: Path) -> None:
    config_path = tmp_path / "config.toml"
    shutil.copyfile(EXAMPLE, config_path)
    config_path.chmod(0o600)  # as the README says to; otherwise the tool warns

    raw = read_config(config_path)
    assert raw is not None
    settings, warnings = resolve_settings(CliOptions(), raw, config_path)

    assert warnings == []
    assert settings.username == "monero"
    assert settings.api_key_type == "demo"
    assert settings.db_path == isolated_home / ".local/share/monero-income/xmr.db"
    assert settings.reports_path == isolated_home / "reports"
    assert settings.timezone is not None
    assert load_zone(settings.timezone).key == settings.timezone
