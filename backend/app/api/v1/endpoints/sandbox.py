"""CIRUS — Sandbox Dry-Run API Endpoint for Policy Verification."""
from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.validators.sandbox_validator import (
    DryRunTestCase,
    PolicySandboxRunner,
    SandboxExecutionReport,
)

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


class SandboxRunRequest(BaseModel):
    policy_code: str
    custom_tests: Optional[List[DryRunTestCase]] = None


@router.post("/dry-run", response_model=SandboxExecutionReport)
async def run_policy_dry_run(payload: SandboxRunRequest) -> SandboxExecutionReport:
    """
    Execute dry-run simulations against an OPA Rego policy to verify enforcement
    against benign and malicious scenarios before deployment.
    """
    try:
        return PolicySandboxRunner.run_rego_sandbox(
            policy_code=payload.policy_code,
            custom_tests=payload.custom_tests,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Dry run execution failed: {str(exc)}")
