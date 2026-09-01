"""CIRUS — API endpoints: Dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.session import get_db
from app.schemas.dashboard import DashboardStats
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _svc(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    dependencies=[Depends(require_api_key)],
)
async def get_dashboard_stats(svc: DashboardService = Depends(_svc)):
    return await svc.get_stats()
