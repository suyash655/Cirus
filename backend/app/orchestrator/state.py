"""CIRUS — Orchestrator: Pipeline state machine."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.utils.time import utcnow


@dataclass
class StageState:
    id: str
    label: str
    description: str
    status: str = "pending"  # pending | running | completed | failed | skipped
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    output: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None
    model_id: Optional[str] = None
    logs: List[str] = field(default_factory=list)

    def start(self) -> None:
        self.status = "running"
        self.started_at = utcnow()

    def complete(
        self,
        output: Dict[str, Any],
        confidence: Optional[float] = None,
        tokens: Optional[int] = None,
        model_id: Optional[str] = None,
    ) -> None:
        self.status = "completed"
        self.completed_at = utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
        self.output = output
        self.confidence = confidence
        self.tokens_used = tokens
        self.model_id = model_id

    def fail(self, reason: str) -> None:
        self.status = "failed"
        self.completed_at = utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
        self.logs.append(f"ERROR: {reason}")

    def skip(self) -> None:
        self.status = "skipped"
        self.completed_at = utcnow()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "output": self.output,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "model_id": self.model_id,
            "logs": self.logs,
        }


@dataclass
class PipelineState:
    """Mutable state object that flows through the pipeline."""

    run_id: str
    incident_id: str
    raw_text: str
    selected_artifacts: List[str]
    stages: List[StageState] = field(default_factory=list)

    # Populated progressively by stages
    extraction: Dict[str, Any] = field(default_factory=dict)
    root_cause: Dict[str, Any] = field(default_factory=dict)
    enrichment_context: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_generated: List[str] = field(default_factory=list)
    risk_score: Optional[Dict[str, Any]] = None
    citations: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    error: Optional[str] = None

    def get_stage(self, stage_id: str) -> Optional[StageState]:
        return next((s for s in self.stages if s.id == stage_id), None)

    def add_tokens(self, tokens: int) -> None:
        self.total_tokens += tokens

    def all_stages_dict(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self.stages]
