from app.core.exceptions import (
    DataNotFoundError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)


def map_finmind_error(status_code: int, msg: str) -> None:
    """Raise appropriate KestrelError based on FinMind HTTP response."""
    match status_code:
        case 402:
            raise ProviderRateLimitError(
                message=f"FinMind quota exceeded: {msg}",
                detail={"provider": "finmind", "original_status": 402},
            )
        case 401 | 403:
            raise ProviderAuthError(
                message="FinMind authentication failed. Check API key.",
                detail={"provider": "finmind", "original_status": status_code},
            )
        case 404:
            raise DataNotFoundError(
                message=f"FinMind dataset not found: {msg}",
                detail={"provider": "finmind"},
            )
        case s if s >= 500:
            raise ProviderUnavailableError(
                message=f"FinMind server error (HTTP {s})",
                detail={"provider": "finmind", "original_status": s},
            )
        case _:
            pass
