"""CIRUS — Pydantic v2 schemas: Citation and ExtractionResult."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

CitationSource = Literal[
    "incident-text", "cloudtrail", "config-drift", "policy-doc", "runbook", "external"
]


class CitationRead(BaseModel):
    id: str
    incident_id: str
    text: str
    source: CitationSource
    relevance: float = Field(ge=0.0, le=1.0)
    line_number: Optional[int] = None
    url: Optional[str] = None

    model_config = {"from_attributes": True}


class CitationCreate(BaseModel):
    text: str
    source: CitationSource
    relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    line_number: Optional[int] = None
    url: Optional[str] = None


class ExtractionResult(BaseModel):
    """Result of the LLM extraction stage — structured data pulled from raw text."""
    title: str
    detected_provider: Literal["AWS", "GCP", "Azure", "Generic"]
    detected_severity: Literal["P1", "P2", "P3", "P4"]
    affected_services: List[str]
    time_range: Dict[str, str]  # {"start": ISO, "end": ISO}
    error_messages: List[str]
    structured_data: Dict[str, Any] = {}
    confidence: float = Field(ge=0.0, le=1.0)
    citations: List[CitationRead] = []
