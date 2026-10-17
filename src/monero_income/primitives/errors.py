"""Errors raised by the primitives layer.

Orchestration translates these into user-facing messages. Messages here describe
what went wrong for a developer; none of them may include a password.
"""


class StorageError(Exception):
    """The local database could not be used."""


class StorageReadError(StorageError):
    """The database file could not be opened or read."""


class StorageWriteError(StorageError):
    """Recording transactions failed; the failed batch was rolled back."""


class SchemaTooNewError(StorageError):
    """The database was written by a newer version of the tool."""

    def __init__(self, found: int) -> None:
        super().__init__(f"database schema version {found} is newer than supported")
        self.found = found


class WalletError(Exception):
    """The wallet RPC could not be used."""


class WalletUnreachableError(WalletError):
    """The wallet could not be reached, or did not answer in time."""


class WalletLoginError(WalletError):
    """The wallet rejected the login, or requires one that was not given."""


class WalletResponseError(WalletError):
    """The wallet answered with something other than the expected JSON-RPC result."""


class WalletRpcError(WalletError):
    """The wallet answered with a JSON-RPC error object."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"{message} (code {code})")
        self.code = code
        self.message = message


class ConfigFileError(Exception):
    """The config file exists but could not be read or parsed."""


class PriceSourceError(Exception):
    """The price source couldn't answer. Messages never include the API key."""


class PriceRateLimitedError(PriceSourceError):
    """The price source refused the request because of its rate limit (HTTP 429)."""

    def __init__(self, retry_after: float | None) -> None:
        super().__init__("the price source is rate-limiting requests")
        self.retry_after = retry_after


class PriceKeyRejectedError(PriceSourceError):
    """The price source rejected the API key (HTTP 401 other than "outside history")."""

    def __init__(self) -> None:
        super().__init__("the price source rejected the API key")


class PriceUnavailableError(PriceSourceError):
    """The price source couldn't be reached or answered with an unusable response."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ImportFileError(Exception):
    """A price import file is unreadable or invalid; the whole file is rejected."""

    def __init__(self, line: int | None, reason: str) -> None:
        super().__init__(f"line {line}: {reason}" if line is not None else reason)
        self.line = line
        self.reason = reason
