"""CIRUS — Citations and Evidence Grounding API Endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.citation_verifier import CitationVerifier, GroundingReport

router = APIRouter(prefix="/citations", tags=["citations"])


class VerifyClaimsPayload(BaseModel):
    raw_text: str | None = None
    summary: str | None = None


@router.get("/{incident_id}/grounding-report", response_model=GroundingReport)
async def get_incident_grounding_report(incident_id: str) -> GroundingReport:
    """
    Get grounded claim report measuring anti-hallucination confidence and exact line citations.
    """
    try:
        return CitationVerifier.verify_incident_grounding(incident_id=incident_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to verify citations: {str(exc)}")


@router.post("/{incident_id}/verify", response_model=GroundingReport)
async def verify_incident_text(incident_id: str, payload: VerifyClaimsPayload) -> GroundingReport:
    """
    Run claim grounding analysis on custom provided incident text.
    """
    try:
        return CitationVerifier.verify_incident_grounding(
            incident_id=incident_id,
            raw_text=payload.raw_text or "",
            generated_summary=payload.summary or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Verification error: {str(exc)}")
