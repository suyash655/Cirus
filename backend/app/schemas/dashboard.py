"""CIRUS — Pydantic v2 schemas: Dashboard statistics."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel


class ArtifactSummary(BaseModel):
    policies: int = 0
    iac_patches: int = 0
    alerts: int = 0
    runbooks: int = 0
    regression_tests: int = 0


class RiskTrendPoint(BaseModel):
    date: str
    avg_risk_before: float
    avg_risk_after: float


class DashboardStats(BaseModel):
    total_incidents: int
    guardrails_generated: int
    avg_risk_reduction: float
    awaiting_approval: int
    artifact_summary: ArtifactSummary
    risk_trend: List[RiskTrendPoint]
    mttg_hours: float = 0.0  # Mean Time to Guardrail in hours
