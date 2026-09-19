"""CIRUS — Alert Ingestion Webhooks: PagerDuty v2 & AWS CloudWatch Alarms.

Both endpoints now create a real Incident in the database and queue the
pipeline via BackgroundTasks, instead of returning a fake success response.

Authentication: Both endpoints require the standard X-API-Key header so
they cannot be triggered by arbitrary internet traffic.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_db, AsyncSessionLocal
from app.schemas.incident import IncidentCreate
from app.services.incident_service import IncidentService
from app.services.workflow_service import WorkflowService

log = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class PagerDutyPayload(BaseModel):
    event: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None


class CloudWatchAlarmPayload(BaseModel):
    AlarmName: str = Field(default="HighUnauthorizedAPICallsAlarm")
    NewStateValue: str = Field(default="ALARM")
    NewStateReason: str = Field(default="Threshold Crossed: rate > 5 unauthorized attempts")
    StateChangeTime: Optional[str] = None
    Region: Optional[str] = "us-east-1"
    AWSAccountId: Optional[str] = "123456789012"


class WebhookIngestResponse(BaseModel):
    status: str
    incident_id: str
    source: str
    pipeline_started: bool
    title: str
    received_at: str


async def _create_and_run(
    raw_text: str,
    severity: str,
    provider: str,
    tags: List[str],
) -> str:
    """Create incident + queue pipeline. Returns the new incident ID."""
    from app.orchestrator.pipeline import CIRUSPipeline

    async with AsyncSessionLocal() as db:
        inc_svc = IncidentService(db)
        wf_svc = WorkflowService(db)

        payload = IncidentCreate(
            raw_text=raw_text,
            severity=severity,  # type: ignore[arg-type]
            provider=provider,  # type: ignore[arg-type]
            selected_artifacts=["rca", "policy", "iac", "runbook"],
            tags=tags,  # type: ignore[call-arg]
        )
        incident = await inc_svc.create_incident(payload)
        run = await wf_svc.create_run(
            incident_id=incident.id,
            model_id=settings.LLM_PROVIDER,
            triggered_by="webhook",
        )
        await db.commit()

    # Try Temporal first, fall back to standalone pipeline run
    try:
        from app.orchestrator.temporal_client import get_temporal_client
        from app.orchestrator.temporal_workflows import CIRUSWorkflow

        client = await get_temporal_client()
        await client.start_workflow(
            CIRUSWorkflow.run,
            args=[run.id, incident.id, raw_text, ["rca", "policy", "iac", "runbook"]],
            id=f"cirus-webhook-{incident.id}",
            task_queue="cirus-task-queue",
        )
    except Exception as temporal_err:
        log.warning("temporal unavailable for webhook, running pipeline inline", error=str(temporal_err))
        async with AsyncSessionLocal() as db2:
            try:
                pipeline = CIRUSPipeline(db2)
                await pipeline.run(run.id, incident.id, raw_text, ["rca", "policy", "iac", "runbook"])
                await db2.commit()
            except Exception as pipe_err:
                await db2.rollback()
                log.error("webhook pipeline failed", incident_id=incident.id, error=str(pipe_err))

    return incident.id


@router.post(
    "/pagerduty",
    response_model=WebhookIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
)
async def ingest_pagerduty_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
) -> WebhookIngestResponse:
    """Ingest PagerDuty v2/v3 webhook event and trigger CIRUS pipeline."""
    try:
        title = "PagerDuty Incident Alert"
        severity_name = "P3"

        if "event" in payload and isinstance(payload["event"], dict):
            data = payload["event"].get("data", {})
            title = data.get("title", title)
            pd_severity = data.get("severity", "").lower()
            severity_name = {"critical": "P1", "error": "P2", "warning": "P3", "info": "P4"}.get(pd_severity, "P3")
        elif "messages" in payload and isinstance(payload["messages"], list) and len(payload["messages"]) > 0:
            inc = payload["messages"][0].get("incident", {})
            title = inc.get("title", title)

        raw_text = (
            f"PagerDuty Alert: {title}\n\n"
            f"Source: PagerDuty\n"
            f"Received: {datetime.now(timezone.utc).isoformat()}\n\n"
            f"Full payload:\n{str(payload)[:2000]}"
        )

        incident_id = await _create_and_run(
            raw_text=raw_text,
            severity=severity_name,
            provider="Generic",
            tags=["pagerduty", "webhook"],
        )

        log.info("pagerduty webhook ingested", incident_id=incident_id, title=title)
        return WebhookIngestResponse(
            status="queued",
            incident_id=incident_id,
            source="PagerDuty",
            pipeline_started=True,
            title=title,
            received_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        log.error("pagerduty webhook failed", error=str(exc))
        raise HTTPException(status_code=400, detail=f"Failed to process PagerDuty payload: {exc}")


@router.post(
    "/cloudwatch",
    response_model=WebhookIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
)
async def ingest_cloudwatch_alarm(
    payload: CloudWatchAlarmPayload,
    background_tasks: BackgroundTasks,
) -> WebhookIngestResponse:
    """Ingest AWS CloudWatch Alarm and trigger CIRUS pipeline."""
    try:
        title = f"AWS CloudWatch: {payload.AlarmName} in {payload.Region}"
        raw_text = (
            f"AWS CloudWatch Alarm Triggered\n\n"
            f"Alarm: {payload.AlarmName}\n"
            f"Region: {payload.Region}\n"
            f"Account: {payload.AWSAccountId}\n"
            f"New State: {payload.NewStateValue}\n"
            f"Reason: {payload.NewStateReason}\n"
            f"Time: {payload.StateChangeTime or datetime.now(timezone.utc).isoformat()}\n"
        )

        incident_id = await _create_and_run(
            raw_text=raw_text,
            severity="P2",
            provider="AWS",
            tags=["cloudwatch", "alarm", "webhook"],
        )

        log.info("cloudwatch alarm ingested", incident_id=incident_id, alarm=payload.AlarmName)
        return WebhookIngestResponse(
            status="queued",
            incident_id=incident_id,
            source="AWS CloudWatch",
            pipeline_started=True,
            title=title,
            received_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        log.error("cloudwatch webhook failed", error=str(exc))
        raise HTTPException(status_code=400, detail=f"Failed to process CloudWatch payload: {exc}")
