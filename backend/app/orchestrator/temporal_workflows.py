"""CIRUS — Orchestrator: Temporal Workflow."""
from datetime import timedelta
from typing import List, Dict, Any
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.orchestrator.temporal_activities import (
        NormalizationInput, RootCauseInput, ContextEnrichmentInput,
        ArtifactGenerationInput, RiskScoringInput,
        CitationExtractionInput, UpdateIncidentStatusInput,
        normalize_incident, classify_root_cause, enrich_context,
        generate_artifacts, score_risk,
        extract_citations, update_incident_status
    )
    # Real eval gate from mlops evaluation package
    from mlops.evaluation.eval_gate_activity import (
        EvalGateInput, EvalGateOutput, run_eval_gate
    )
    # GitHub PR activity (Phase 6)
    from app.services.github_pr_activity import (
        GitHubPRInput, GitHubPROutput, open_github_pr
    )

@workflow.defn
class CIRUSWorkflow:
    @workflow.run
    async def run(
        self,
        run_id: str,
        incident_id: str,
        raw_text: str,
        selected_artifacts: List[str]
    ) -> Dict[str, Any]:
        
        # We will add semantic cache check here in Phase 4.
        
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=5,
        )

        # 1. Normalization
        norm_out = await workflow.execute_activity(
            normalize_incident,
            NormalizationInput(raw_text=raw_text),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        # 2. Root Cause
        rc_out = await workflow.execute_activity(
            classify_root_cause,
            RootCauseInput(raw_text=raw_text, extraction=norm_out.extraction),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        # 3. Context Enrichment
        enrich_out = await workflow.execute_activity(
            enrich_context,
            ContextEnrichmentInput(root_cause=rc_out.root_cause),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )

        # 4. Artifact Generation
        art_out = await workflow.execute_activity(
            generate_artifacts,
            ArtifactGenerationInput(
                incident_id=incident_id,
                raw_text=raw_text,
                selected_artifacts=selected_artifacts,
                root_cause=rc_out.root_cause,
                extraction=norm_out.extraction,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        # 5. Real Eval Gate (replaces stub from prior pass)
        eval_out = await workflow.execute_activity(
            run_eval_gate,
            EvalGateInput(
                incident_id=incident_id,
                artifacts_generated=art_out.generated,
                raw_text=raw_text,
                root_cause=rc_out.root_cause,
                extraction=norm_out.extraction,
                enrichment_context=enrich_out.enrichment_context,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=2),
                maximum_attempts=2,  # Eval gate failures are usually deterministic
            ),
        )
        if not eval_out.passed:
            await workflow.execute_activity(
                update_incident_status,
                UpdateIncidentStatusInput(incident_id=incident_id, status="error"),
                start_to_close_timeout=timedelta(seconds=10),
            )
            return {
                "status": "failed",
                "reason": "eval_gate_failed",
                "issues": eval_out.issues,
                "scores": eval_out.scores,
            }

        # 6. Risk Scoring
        risk_out = await workflow.execute_activity(
            score_risk,
            RiskScoringInput(
                root_cause=rc_out.root_cause,
                extraction=norm_out.extraction,
                artifacts_generated=art_out.generated
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        # 7. Citation Extraction
        cite_out = await workflow.execute_activity(
            extract_citations,
            CitationExtractionInput(raw_text=raw_text),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )
        
        # 8. GitHub PR (Phase 6 — non-blocking: pipeline succeeds regardless)
        # Reads incident_reference from run metadata; falls back to incident_id
        incident_reference = workflow.info().workflow_id
        # Extract INC-XXX from workflow ID if set by incident.io trigger
        import re as _re
        _match = _re.search(r'(INC-\d+)', incident_reference)
        incident_reference = _match.group(1) if _match else f"INC-{incident_id[:8].upper()}"

        pr_out = await workflow.execute_activity(
            open_github_pr,
            GitHubPRInput(
                incident_id=incident_id,
                incident_reference=incident_reference,
                eval_scores=eval_out.scores,
            ),
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                maximum_attempts=2,
            ),
        )

        # 9. Mark Complete
        await workflow.execute_activity(
            update_incident_status,
            UpdateIncidentStatusInput(incident_id=incident_id, status="ready"),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=retry_policy,
        )

        return {
            "status": "completed",
            "artifacts_generated": art_out.generated,
            "github_pr": {
                "action": pr_out.action,
                "pr_url": pr_out.pr_url,
                "pr_number": pr_out.pr_number,
            },
        }
