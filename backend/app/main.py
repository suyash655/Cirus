"""CIRUS — FastAPI application entry point."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import CIRUSException, cirus_exception_handler
from app.core.logging import configure_logging, get_logger
from app.db.session import engine
from app.db.base import Base

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info(
        "CIRUS backend starting",
        environment=settings.ENVIRONMENT,
        mode=settings.MODE,
        llm_provider=settings.LLM_PROVIDER,
    )
    # Auto-create tables in development; use Alembic in staging/production
    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    log.info("CIRUS backend shutting down")
    await engine.dispose()


app = FastAPI(
    title="CIRUS API",
    description=(
        "Production-grade AI backend for cloud incident response and "
        "prevention artifact generation."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    log.debug(
        "request handled",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration_ms,
    )
    return response


# ── Exception Handlers ────────────────────────────────────────────────────────

app.add_exception_handler(CIRUSException, cirus_exception_handler)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    log.warning(
        "request validation failed",
        path=request.url.path,
        errors=exc.errors(),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {
        "status": "ok",
        "product": "CIRUS",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "mode": settings.MODE,
    }
