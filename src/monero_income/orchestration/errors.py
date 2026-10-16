"""The single error type the CLI needs to know about."""


class RunError(Exception):
    """User-facing failure. str(error) is the complete message, with no 'Error:' prefix."""
