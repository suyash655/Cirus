"""CIRUS — Domain exceptions and FastAPI error handlers."""
from __future__ import annotations

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
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "detail": {},
            }
        },
    )
