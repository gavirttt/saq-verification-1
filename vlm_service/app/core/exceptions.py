"""Maps domain errors to HTTP responses. This is the ONLY place the api
layer is allowed to know about domain exception types in detail — routes
themselves just let exceptions propagate to this handler."""
from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.domain.errors import (
    DomainError,
    ImageProcessingError,
    JobNotFoundError,
    ResultNotFoundError,
    SiteNotFoundError,
    VLMResponseError,
    VLMUnavailableError,
)

_STATUS_MAP: dict[type[DomainError], int] = {
    SiteNotFoundError: status.HTTP_404_NOT_FOUND,
    ResultNotFoundError: status.HTTP_404_NOT_FOUND,
    JobNotFoundError: status.HTTP_404_NOT_FOUND,
    ImageProcessingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    VLMResponseError: status.HTTP_502_BAD_GATEWAY,
    VLMUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _status_for(exc: DomainError) -> int:
    for exc_type, code in _STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return code
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})


def register_exception_handlers(app) -> None:  # type: ignore[no-untyped-def]
    app.add_exception_handler(DomainError, domain_error_handler)
