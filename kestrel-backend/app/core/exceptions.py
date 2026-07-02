from typing import Any


class KestrelError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ):
        # All of message/status_code/error_code default to the class-level values
        # but can be overridden per-instance, so callers can e.g. raise an
        # AuthorizationError as 401 vs 403, or attach a specific error_code,
        # without needing a dedicated subclass for every variation.
        self.message = message or self.__class__.message
        self.status_code = status_code if status_code is not None else self.__class__.status_code
        self.error_code = error_code or self.__class__.error_code
        self.detail = detail or {}
        super().__init__(self.message)


# --- Provider errors ---


class ProviderError(KestrelError):
    status_code = 502
    error_code = "PROVIDER_ERROR"
    message = "Data provider error"


class ProviderRateLimitError(ProviderError):
    status_code = 429
    error_code = "PROVIDER_RATE_LIMITED"
    message = "Data provider rate limit exceeded. Please retry later."


class ProviderUnavailableError(ProviderError):
    status_code = 503
    error_code = "PROVIDER_UNAVAILABLE"
    message = "Data provider is temporarily unavailable"


class ProviderAuthError(ProviderError):
    status_code = 502
    error_code = "PROVIDER_AUTH_FAILED"
    message = "Data provider authentication failed"


class DataNotFoundError(ProviderError):
    status_code = 404
    error_code = "DATA_NOT_FOUND"
    message = "Requested data not found"


class TierInsufficientError(ProviderError):
    status_code = 403
    error_code = "TIER_INSUFFICIENT"
    message = "Your subscription tier does not support this dataset"


# --- Client errors ---


class ValidationError(KestrelError):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Request validation failed"


class AuthenticationError(KestrelError):
    status_code = 401
    error_code = "AUTHENTICATION_REQUIRED"
    message = "Authentication required"


class AuthorizationError(KestrelError):
    status_code = 403
    error_code = "FORBIDDEN"
    message = "You do not have permission to perform this action"


class NotFoundError(KestrelError):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class RateLimitError(KestrelError):
    status_code = 429
    error_code = "RATE_LIMITED"
    message = "API rate limit exceeded"
