"""Custom exceptions shared by all Ledgerly modules."""


class LedgerlyError(Exception):
    """Base class for all application errors."""


class ValidationError(LedgerlyError):
    """Raised when user input is invalid (bad amount, date, type...)."""


class NotFoundError(LedgerlyError):
    """Raised when a requested record does not exist."""
