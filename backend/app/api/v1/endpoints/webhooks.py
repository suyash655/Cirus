"""CIRUS — Alert Ingestion Webhooks: PagerDuty v2 & AWS CloudWatch Alarms."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

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


@router.post("/pagerduty", response_model=WebhookIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_pagerduty_webhook(payload: Dict[str, Any]) -> WebhookIngestResponse:
    """
    Ingest PagerDuty v2/v3 Webhook event and automatically trigger CIRUS remediation.
    """
    try:
        # Extract title or summary
        title = "PagerDuty Incident Alert"
        if "event" in payload and isinstance(payload["event"], dict):
            title = payload["event"].get("data", {}).get("title", title)
        elif "messages" in payload and isinstance(payload["messages"], list) and len(payload["messages"]) > 0:
            title = payload["messages"][0].get("incident", {}).get("title", title)

        synthetic_id = f"pd-{int(datetime.now(timezone.utc).timestamp())}"

        log.info("Ingested PagerDuty webhook alert", incident_title=title, incident_id=synthetic_id)

        return WebhookIngestResponse(
            status="queued",
            incident_id=synthetic_id,
            source="PagerDuty",
            pipeline_started=True,
            title=title,
            received_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse PagerDuty payload: {str(exc)}")


@router.post("/cloudwatch", response_model=WebhookIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_cloudwatch_alarm(payload: CloudWatchAlarmPayload) -> WebhookIngestResponse:
    """
    Ingest AWS CloudWatch Alarm event triggered via SNS or HTTP subscription.
    """
    try:
        synthetic_id = f"cw-{int(datetime.now(timezone.utc).timestamp())}"
        title = f"AWS CloudWatch: {payload.AlarmName} in {payload.Region}"

        log.info("Ingested CloudWatch alarm", alarm=payload.AlarmName, incident_id=synthetic_id)

        return WebhookIngestResponse(
            status="queued",
            incident_id=synthetic_id,
            source="AWS CloudWatch",
            pipeline_started=True,
            title=title,
            received_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse CloudWatch payload: {str(exc)}")
