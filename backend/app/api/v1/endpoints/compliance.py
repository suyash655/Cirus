"""CIRUS — API endpoint for incident compliance reports (SOC 2 & CIS)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.schemas.compliance import IncidentComplianceReport
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/{incident_id}", response_model=IncidentComplianceReport)
async def get_incident_compliance(
    incident_id: str,
    provider: str = Query("AWS", description="Cloud provider (AWS, GCP, Azure)"),
    severity: str = Query("P1", description="Severity level"),
) -> IncidentComplianceReport:
    """
    Get audit-ready SOC 2 Type II and CIS benchmark compliance mapping
    for all prevention artifacts generated for the given incident.
    """
    try:
        report = ComplianceService.generate_compliance_report(
            incident_id=incident_id,
            provider=provider,
            severity=severity,
        )
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate compliance report: {str(exc)}")
