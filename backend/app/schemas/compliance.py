"""CIRUS — Compliance schemas for SOC 2 Type II and CIS benchmarks."""
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ComplianceControl(BaseModel):
    id: str = Field(..., description="Control ID e.g. CC6.1, CC6.6, CIS-AWS-1.20")
    framework: Literal["SOC2_TYPE_II", "CIS_BENCHMARK", "ISO_27001", "NIST_800_53"]
    name: str = Field(..., description="Control title or description")
    description: str
    status: Literal["VERIFIED", "PARTIALLY_SATISFIED", "REMEDIATION_REQUIRED"]
    satisfying_artifact: str = Field(..., description="Artifact type e.g. policy, iac, alerts")
    claim_details: str = Field(..., description="Explanation of how the generated artifact satisfies the control")
    evidence_citation: Optional[str] = Field(None, description="Direct quote or log evidence backing this claim")


class IncidentComplianceReport(BaseModel):
    incident_id: str
    overall_compliance_score: float = Field(..., ge=0.0, le=100.0)
    audit_readiness_status: Literal["AUDIT_READY", "ACTION_REQUIRED", "NON_COMPLIANT"]
    verified_claims_count: int
    soc2_controls: List[ComplianceControl]
    cis_benchmarks: List[ComplianceControl]
    audit_notes: str
    generated_at: str
