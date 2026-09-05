"""CIRUS — GitOps API Endpoints for one-click Pull Request creation."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.gitops_service import CreatePRRequest, GitOpsPRResponse, GitOpsService

router = APIRouter(prefix="/gitops", tags=["gitops"])


@router.post("/create-pr", response_model=GitOpsPRResponse)
async def create_gitops_pr(payload: CreatePRRequest) -> GitOpsPRResponse:
    """
    Publish generated prevention artifacts as a Pull Request in the target infrastructure repository.
    """
    try:
        return GitOpsService.create_remediation_pr(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create GitOps PR: {str(exc)}")
