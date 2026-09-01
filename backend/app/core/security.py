"""CIRUS — API key-based security layer."""
from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

_api_key_scheme = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_api_key_scheme),
) -> str:
    """FastAPI dependency that enforces API key authentication.

    In local mock development with no keys configured the guard is bypassed.
    In all other environments a valid key must be provided.
    """
    if (
        settings.ENVIRONMENT == "development"
        and settings.MODE == "mock"
        and not settings.allowed_api_keys_list
    ):
        return "dev-bypass"

    if api_key is None or api_key not in settings.allowed_api_keys_list:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing API key.",
            },
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
