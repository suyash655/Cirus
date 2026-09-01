"""CIRUS — SQLAlchemy ORM model: Incident."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.run import WorkflowRun
    from app.models.artifact import Artifact
    from app.models.citation import Citation


class Severity(str, enum.Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class CloudProvider(str, enum.Enum):
    AWS = "AWS"
    GCP = "GCP"
    Azure = "Azure"
    Generic = "Generic"


class IncidentStatus(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    error = "error"
    partial = "partial"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    detected_format: Mapped[str] = mapped_column(String(20), default="plain")
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, native_enum=False), default=Severity.P3
    )
    provider: Mapped[CloudProvider] = mapped_column(
        Enum(CloudProvider, native_enum=False), default=CloudProvider.Generic
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False), default=IncidentStatus.processing
    )
    # JSON arrays stored as text for SQLite compatibility
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    artifacts_ready: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="[]")
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    runs: Mapped[List["WorkflowRun"]] = relationship(
        "WorkflowRun", back_populates="incident", cascade="all, delete-orphan"
    )
    artifacts: Mapped[List["Artifact"]] = relationship(
        "Artifact", back_populates="incident", cascade="all, delete-orphan"
    )
    citations: Mapped[List["Citation"]] = relationship(
        "Citation", back_populates="incident", cascade="all, delete-orphan"
    )
