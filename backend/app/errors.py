"""Error types raised by services and AI code; mapped to HTTP responses by app handlers."""


class ApiError(Exception):
    """Base class for errors that map onto an HTTP status at the API boundary."""

    status_code: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(ApiError):
    status_code = 404


class ConflictError(ApiError):
    status_code = 409


class BadRequestError(ApiError):
    status_code = 400


class AIError(ApiError):
    """The AI backend failed (transport, auth, or out-of-contract response)."""

    status_code = 502


class AIFormatError(AIError):
    """The AI responded with content that violates the wrapper's output contract."""


class ConfigError(ApiError):
    """Required configuration (RES-001 env vars) is missing at call time."""

    status_code = 503
