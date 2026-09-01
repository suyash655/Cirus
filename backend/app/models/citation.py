"""CIRUS — SQLAlchemy ORM model: Citation."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident


class CitationSource(str, enum.Enum):
    incident_text = "incident-text"
    cloudtrail = "cloudtrail"
    config_drift = "config-drift"
    policy_doc = "policy-doc"
    runbook = "runbook"
    external = "external"


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[CitationSource] = mapped_column(
        Enum(CitationSource, native_enum=False), nullable=False
    )
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    incident: Mapped["Incident"] = relationship("Incident", back_populates="citations")
