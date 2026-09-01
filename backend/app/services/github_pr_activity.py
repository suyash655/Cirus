"""CIRUS — Activity: Open GitHub PR after pipeline completes with a passing eval gate."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from temporalio import activity

log = logging.getLogger(__name__)


@dataclass
class GitHubPRInput:
    incident_id: str
    incident_reference: str          # e.g. "INC-104" from incident.io, or CIRUS fallback
    eval_scores: Dict[str, float]
    postmortem_url: Optional[str] = None


@dataclass
class GitHubPROutput:
    action: str                      # "created" | "updated" | "skipped" | "failed"
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    error: Optional[str] = None


@activity.defn
async def open_github_pr(input_data: GitHubPRInput) -> GitHubPROutput:
    """
    Temporal Activity: retrieve artifacts from DB and open a GitHub PR.

    FAILURE PATHS:
    - GitHub not configured: returns action="skipped" (no exception — pipeline succeeds)
    - GitHub auth fails: returns action="failed" with error (no exception — incident stays "ready")
    - Duplicate PR: returns action="updated" — existing PR body refreshed
    - Eval gate failed: this activity is NOT called (workflow returns early)
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.artifact import ArtifactType
        from app.repositories.artifact_repository import ArtifactRepository
        from app.repositories.incident_repository import IncidentRepository
        from app.utils.json_repair import parse_llm_json

        # Load incident + artifacts from DB
        async with AsyncSessionLocal() as session:
            inc_repo = IncidentRepository(session)
            artifact_repo = ArtifactRepository(session)

            incident = await inc_repo.get(input_data.incident_id)
            if not incident:
                return GitHubPROutput(action="skipped", error="Incident not found")

            artifacts_db = await artifact_repo.list_by_incident(input_data.incident_id)

        # Build artifacts dict: {"policy": code_str, "iac": hcl_str, "rca": {...}, ...}
        artifacts: Dict[str, Any] = {}
        rca_summary = ""

        for art in artifacts_db:
            content = parse_llm_json(art.content, default={})
            atype = art.artifact_type.value

            if atype == "policy":
                artifacts["policy"] = content.get("code", "")
            elif atype == "iac":
                artifacts["iac"] = content.get("fullPatch") or content.get("diff") or ""
            elif atype == "rca":
                artifacts["rca"] = content
                rca_summary = content.get("executiveSummary", "")
            elif atype == "runbook":
                artifacts["runbook"] = content

        if not artifacts:
            return GitHubPROutput(action="skipped", error="No artifacts found")

        # Open the PR
        from app.services.github_integration import open_prevention_pr
        result = await open_prevention_pr(
            incident_reference=input_data.incident_reference,
            cirus_incident_id=input_data.incident_id,
            artifacts=artifacts,
            rca_summary=rca_summary,
            eval_scores=input_data.eval_scores,
            postmortem_url=input_data.postmortem_url,
        )

        return GitHubPROutput(
            action=result.get("action", "unknown"),
            pr_url=result.get("pr_url"),
            pr_number=result.get("pr_number"),
        )

    except RuntimeError as e:
        # Auth failures surface here
        activity.logger.error(f"GitHub PR creation failed: {e}")
        return GitHubPROutput(action="failed", error=str(e))
    except Exception as e:
        activity.logger.error(f"Unexpected error in GitHub PR activity: {e}")
        return GitHubPROutput(action="failed", error=str(e))
