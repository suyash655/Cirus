"""CIRUS — SQLAlchemy ORM model: WorkflowRun."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident


class WorkflowRunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[WorkflowRunStatus] = mapped_column(
        Enum(WorkflowRunStatus, native_enum=False), default=WorkflowRunStatus.queued
    )
    current_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # JSON array of WorkflowStage objects
    stages: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    model_id: Mapped[str] = mapped_column(String(100), default="mock")
    triggered_by: Mapped[str] = mapped_column(String(20), default="auto")
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="runs")
