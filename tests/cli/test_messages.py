"""FR-019: user-facing text says "transactions", never "transfers".

Every string literal in the layers that produce user-facing messages (the CLI and
orchestration) is checked. Primitives aren't scanned: that's where the wallet's
``get_transfers`` RPC name lives, and their messages reach users only through
orchestration's wording.
"""

import ast
from pathlib import Path

import monero_income

PACKAGE = Path(monero_income.__file__).parent
USER_FACING = [PACKAGE / "cli.py", *sorted((PACKAGE / "orchestration").glob("*.py"))]


def string_literals(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(), filename=str(path))
    return [
        (node.lineno, node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def test_scan_covers_the_user_facing_modules() -> None:
    names = {path.name for path in USER_FACING}
    assert {"cli.py", "run.py", "settings.py", "sync.py"} <= names
    # Feature 002's user-facing wording lives here too.
    assert {"pricing.py", "price_import.py", "valuation.py"} <= names


def test_no_user_facing_string_says_transfer() -> None:
    offending = [
        f"{path.relative_to(PACKAGE)}:{line}: {text!r}"
        for path in USER_FACING
        for line, text in string_literals(path)
        if "transfer" in text.lower()
    ]

    assert offending == []
