"""CIRUS — Pydantic v2 schemas: Incident."""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field, model_validator


# ── Enums (mirrors ORM enums) ─────────────────────────────────────────────────

Severity = Literal["P1", "P2", "P3", "P4"]
CloudProvider = Literal["AWS", "GCP", "Azure", "Generic"]
IncidentStatus = Literal["processing", "ready", "error", "partial"]
ArtifactType = Literal["rca", "policy", "iac", "alerts", "runbook", "regression"]
InputMethod = Literal["paste", "upload"]
DetectedFormat = Literal["json", "yaml", "markdown", "plain"]


# ── Timeline ──────────────────────────────────────────────────────────────────

class TimelineEventRead(BaseModel):
    id: str
    timestamp: str
    title: str
    description: str
    type: Literal["detection", "impact", "mitigation", "resolution", "root-cause"]


# ── Create ────────────────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    raw_text: str = Field(
        ...,
        min_length=10,
        validation_alias=AliasChoices("raw_text", "rawText"),
        description="Raw incident log text or structured report.",
    )
    input_method: InputMethod = Field(
        default="paste",
        validation_alias=AliasChoices("input_method", "inputMethod"),
    )
    file_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("file_name", "fileName"),
    )
    selected_artifacts: List[ArtifactType] = Field(
        default_factory=lambda: ["rca", "runbook"],
        validation_alias=AliasChoices("selected_artifacts", "selectedArtifacts"),
        description="Which artifact types to generate.",
    )
    severity: Optional[Severity] = None
    provider: Optional[CloudProvider] = None

    @model_validator(mode="after")
    def at_least_one_artifact(self) -> "IncidentCreate":
        if not self.selected_artifacts:
            raise ValueError("At least one artifact type must be selected.")
        return self


# ── Read ──────────────────────────────────────────────────────────────────────

class IncidentRead(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    severity: Severity
    provider: CloudProvider
    status: IncidentStatus
    tags: List[str]
    artifacts_ready: List[ArtifactType]
    file_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentDetailRead(IncidentRead):
    raw_text: str
    detected_format: DetectedFormat
    timeline: List[TimelineEventRead] = []


# ── List ──────────────────────────────────────────────────────────────────────

class IncidentListResponse(BaseModel):
    items: List[IncidentRead]
    total: int


# ── Create response ───────────────────────────────────────────────────────────

class IncidentCreateResponse(BaseModel):
    id: str
    estimated_processing_ms: int


# ── Update (patch) ────────────────────────────────────────────────────────────

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    severity: Optional[Severity] = None
    provider: Optional[CloudProvider] = None
    tags: Optional[List[str]] = None
