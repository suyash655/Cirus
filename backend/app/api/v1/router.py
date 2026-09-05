"""CIRUS — API v1 router: registers all endpoint routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    incidents,
    runs,
    artifacts,
    dashboard,
    knowledge,
    exports,
    compliance,
    citations,
    gitops,
    webhooks,
    sandbox,
)
from app.services.incident_io_webhook import router as webhook_router

api_router = APIRouter()

api_router.include_router(incidents.router)
api_router.include_router(runs.router)
api_router.include_router(artifacts.router)
api_router.include_router(dashboard.router)
api_router.include_router(knowledge.router)
api_router.include_router(exports.router)
api_router.include_router(compliance.router)
api_router.include_router(citations.router)
api_router.include_router(gitops.router)
api_router.include_router(webhooks.router)
api_router.include_router(sandbox.router)
api_router.include_router(webhook_router)
