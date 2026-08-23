"""backend/app/api/errors.py

Typed domain exceptions and FastAPI error-handling middleware.

Design decisions:
  - One canonical error response envelope: {code, message, request_id, details?}
  - All domain exception types are defined here and translated to HTTP status
    codes in one place (exception handlers on the app).
  - HTTP layer never leaks internal traceback or sensitive information.
  - request_id is a UUID attached to every request via middleware so all log
    lines for a single request can be correlated.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger(__name__)


# ── Domain exceptions ──────────────────────────────────────────────────────────


class DomainError(Exception):
    """Base class for all CaseClock domain errors.

    Subclasses map to specific HTTP status codes in `install_error_handlers`.
    Do not raise bare `DomainError`; always use a concrete subclass so the
    HTTP layer can translate it unambiguously.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(DomainError):
    """Requested resource does not exist or is out of scope for the principal.

    Maps to HTTP 404.  Use this both for truly missing resources and for
    resources the caller is not authorized to see (to avoid enumeration).
    """


class ForbiddenError(DomainError):
    """Principal is authenticated but lacks authorization for this action.

    Maps to HTTP 403.
    """


class ConflictError(DomainError):
    """Optimistic concurrency conflict: the resource was modified since last read.

    Maps to HTTP 409.  Clients should reload and retry with the new version.
    """


class ValidationError(DomainError):
    """Business-rule validation failure (not an HTTP body parsing error).

    Maps to HTTP 422.  Pydantic parsing errors are a separate path handled
    by FastAPI's built-in validation middleware.
    """


class ExternalServiceUnavailableError(DomainError):
    """Catalyst Data Store, QuickML, SmartBrowz, or another external dependency
    is unavailable or returned an unexpected error.

    Maps to HTTP 503.  The response should include a retry-after hint if
    the upstream error includes one.
    """


class RateLimitError(DomainError):
    """Per-principal or per-IP rate limit has been exceeded.

    Maps to HTTP 429.
    """


# ── Error envelope ─────────────────────────────────────────────────────────────


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id or "unknown",
    }
    if details:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


# ── Request correlation middleware ─────────────────────────────────────────────

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a UUID correlation ID to every request.

    - If the caller supplies ``X-Request-ID``, reuse it.
    - Otherwise generate a new UUIDv4.
    - Echo the ID back in the response header so callers can correlate.
    - Store on ``request.state.request_id`` for handlers and loggers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


# ── Exception handlers ─────────────────────────────────────────────────────────


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def _handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(404, "not_found", exc.message, _get_request_id(request), exc.details)


async def _handle_forbidden(request: Request, exc: ForbiddenError) -> JSONResponse:
    return _error_response(403, "forbidden", exc.message, _get_request_id(request), exc.details)


async def _handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return _error_response(409, "conflict", exc.message, _get_request_id(request), exc.details)


async def _handle_validation(request: Request, exc: ValidationError) -> JSONResponse:
    return _error_response(422, "validation_error", exc.message, _get_request_id(request), exc.details)


async def _handle_external_unavailable(
    request: Request, exc: ExternalServiceUnavailableError
) -> JSONResponse:
    logger.error("External service unavailable: %s", exc.message, extra={"request_id": _get_request_id(request)})
    return _error_response(503, "service_unavailable", exc.message, _get_request_id(request), exc.details)


async def _handle_rate_limit(request: Request, exc: RateLimitError) -> JSONResponse:
    return _error_response(429, "rate_limit_exceeded", exc.message, _get_request_id(request), exc.details)


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    request_id = _get_request_id(request)
    logger.exception("Unhandled exception [request_id=%s]", request_id)
    return _error_response(
        500,
        "internal_error",
        "An unexpected error occurred. Please include the request_id when reporting.",
        request_id,
    )


# ── Install all handlers on the app ───────────────────────────────────────────


def install_error_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers and the request-ID middleware.

    Call this once during app factory creation, before including routers.
    """
    app.add_middleware(RequestIDMiddleware)

    app.add_exception_handler(NotFoundError, _handle_not_found)  # type: ignore[arg-type]
    app.add_exception_handler(ForbiddenError, _handle_forbidden)  # type: ignore[arg-type]
    app.add_exception_handler(ConflictError, _handle_conflict)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, _handle_validation)  # type: ignore[arg-type]
    app.add_exception_handler(ExternalServiceUnavailableError, _handle_external_unavailable)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitError, _handle_rate_limit)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _handle_unexpected)  # type: ignore[arg-type]
