"""CIRUS — Domain exceptions and FastAPI error handlers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse


# ── Base ──────────────────────────────────────────────────────────────────────

class CIRUSException(Exception):
    """Base exception for all CIRUS domain errors."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: dict | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


# ── Concrete exceptions ───────────────────────────────────────────────────────

class NotFoundError(CIRUSException):
    def __init__(self, resource: str, id: str) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} '{id}' not found.",
            status_code=404,
            detail={"resource": resource, "id": id},
        )


class ValidationError(CIRUSException):
    def __init__(self, message: str, detail: dict | None = None) -> None:
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            detail=detail,
        )


class ConflictError(CIRUSException):
    def __init__(self, message: str) -> None:
        super().__init__(code="CONFLICT", message=message, status_code=409)


class AuthenticationError(CIRUSException):
    def __init__(self, message: str = "Invalid or missing API key.") -> None:
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)


class AuthorizationError(CIRUSException):
    def __init__(self, message: str = "Permission denied.") -> None:
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class RateLimitError(CIRUSException):
    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        retry_after: int = 60,
    ) -> None:
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
            detail={"retry_after": retry_after},
        )
        self.retry_after = retry_after


class ServiceUnavailableError(CIRUSException):
    def __init__(self, service: str, message: str = "Service temporarily unavailable.") -> None:
        super().__init__(
            code="SERVICE_UNAVAILABLE",
            message=message,
            status_code=503,
            detail={"service": service},
        )


class PipelineError(CIRUSException):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(
            code="PIPELINE_ERROR",
            message=message,
            status_code=500,
            detail={"stage": stage},
        )


class LLMError(CIRUSException):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(
            code="LLM_ERROR",
            message=message,
            status_code=502,
            detail={"provider": provider},
        )


class ExternalServiceError(CIRUSException):
    def __init__(self, service: str, message: str) -> None:
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=message,
            status_code=502,
            detail={"service": service},
        )


class ArtifactGenerationError(CIRUSException):
    def __init__(self, artifact_type: str, message: str) -> None:
        super().__init__(
            code="ARTIFACT_GENERATION_ERROR",
            message=message,
            status_code=500,
            detail={"artifact_type": artifact_type},
        )


class ExportError(CIRUSException):
    def __init__(self, message: str) -> None:
        super().__init__(code="EXPORT_ERROR", message=message, status_code=500)


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cirus_exception_handler(request: Request, exc: CIRUSException) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    headers = {"X-Request-ID": request_id}
    if isinstance(exc, RateLimitError):
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        headers=headers,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    return JSONResponse(
        status_code=500,
        headers={"X-Request-ID": request_id},
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "detail": {},
                "path": str(request.url.path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": request_id,
            }
        },
    )
