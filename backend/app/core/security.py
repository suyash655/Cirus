"""CIRUS — API key-based security layer."""
from __future__ import annotations

import logging

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

log = logging.getLogger(__name__)

_INSECURE_SECRET = "CHANGE_ME_USE_STRONG_SECRET_IN_PRODUCTION"

_api_key_scheme = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


def validate_secret_key() -> None:
    """Raise at startup if SECRET_KEY is the placeholder in non-dev environments."""
    if settings.ENVIRONMENT != "development" and settings.SECRET_KEY == _INSECURE_SECRET:
        raise RuntimeError(
            "SECRET_KEY is set to the insecure placeholder value. "
            "Set a strong random secret before running in staging/production. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )


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
        log.warning(
            "AUTH BYPASS ACTIVE — no API keys configured in development/mock mode. "
            "This must never happen in staging or production."
        )
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
