"""CIRUS — Pydantic v2 schemas: Risk scoring."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RiskDimension(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    label: str
    description: str


class RiskDimensions(BaseModel):
    exposure: RiskDimension
    blast_radius: RiskDimension
    recurrence: RiskDimension
    remediation_effort: RiskDimension


class RiskScoreRead(BaseModel):
    incident_id: str
    overall: float = Field(ge=0.0, le=100.0)
    dimensions: RiskDimensions
    before_remediation: float = Field(ge=0.0, le=100.0)
    after_remediation: float = Field(ge=0.0, le=100.0)
    delta: float  # positive = improvement
    calculated_at: str
