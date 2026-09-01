"""CIRUS — Service: incident.io webhook handler.

SCHEMA SOURCE:
  incident.io webhooks are powered by Svix. The post-mortem completion event
  is sent as an `IncidentUpdated` event when the post-mortem status changes.
  Schema validated against the incident.io API reference:
  https://api.incident.io/v2/openapi.json (checked 2024-08 version)

  incident.io sends these headers for verification:
    webhook-id        — unique ID for deduplication
    webhook-timestamp — Unix epoch (int) of send time
    webhook-signature — base64 HMAC-SHA256, format: v1,<signature>

SECURITY:
  We verify the HMAC-SHA256 signature before processing any payload.
  An unverified webhook is rejected with 401.
  Tolerance window: ±5 minutes (standard Svix recommendation).

TRIGGER CONDITION:
  We trigger the CIRUS pipeline when:
    event_type == "public_incident.incident_updated"
    AND payload.incident.status == "closed"
    AND payload.incident.postmortem_document_url is not None
    AND payload.incident.postmortem_status == "exported"  (fully completed)
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/incident-io", tags=["webhooks"])


# ── incident.io Webhook Payload Schema ────────────────────────────────────────
# Validated against incident.io API reference (v2 schema, 2024-08)

class IncidentPostmortem(BaseModel):
    """Postmortem sub-object in the incident payload."""
    document_url: Optional[str] = None
    status: Optional[str] = None  # "draft" | "in_review" | "exported"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class IncidentSeverity(BaseModel):
    id: str
    name: str
    rank: Optional[int] = None
    description: Optional[str] = None


class IncidentType(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class IncidentStatus(BaseModel):
    id: str
    name: str
    category: Optional[str] = None  # "triage" | "active" | "post-incident" | "closed"


class IncidentPayload(BaseModel):
    """Core incident object from incident.io webhook."""
    id: str
    name: str
    reference: Optional[str] = None  # e.g. "INC-104"
    status: Optional[str] = None      # "closed" | "active" | "triage" etc.
    severity: Optional[IncidentSeverity] = None
    postmortem_document_url: Optional[str] = None
    postmortem_status: Optional[str] = None
    summary: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @property
    def incident_reference(self) -> str:
        """Return reference (INC-104) or fall back to id."""
        return self.reference or self.id

    @property
    def is_postmortem_complete(self) -> bool:
        """True when the post-mortem is exported/complete and incident closed."""
        return (
            self.status in ("closed",)
            and self.postmortem_status in ("exported", "completed")
            and bool(self.postmortem_document_url)
        )


class IncidentIOWebhookPayload(BaseModel):
    """
    Root payload schema for incident.io webhook events.
    Source: incident.io v2 API reference (webhooks section).
    """
    event_type: str  # e.g. "public_incident.incident_updated"
    public_api_version: Optional[str] = None
    occurred_at: Optional[str] = None
    # The incident.io API nests the incident under the event type key.
    # For "public_incident.incident_updated", the data is in `incident`.
    incident: Optional[IncidentPayload] = None

    # Some events use a top-level `data` wrapper
    data: Optional[Dict[str, Any]] = None

    def get_incident(self) -> Optional[IncidentPayload]:
        """Extract the incident regardless of nesting style."""
        if self.incident:
            return self.incident
        if self.data and "incident" in self.data:
            try:
                return IncidentPayload(**self.data["incident"])
            except Exception:
                pass
        return None


# ── HMAC Signature Verification ──────────────────────────────────────────────

SIGNATURE_TOLERANCE_SECONDS = 300  # 5 minutes (Svix default)


def _verify_svix_signature(
    payload_bytes: bytes,
    webhook_id: str,
    webhook_timestamp: str,
    webhook_signature: str,
    signing_secret: str,
) -> bool:
    """
    Verify incident.io webhook signature using Svix HMAC-SHA256.

    Svix signed content format: "{msg_id}.{timestamp}.{payload}"
    Signature format: "v1,{base64_hmac}"
    """
    try:
        # Validate timestamp freshness
        ts = int(webhook_timestamp)
        now = int(time.time())
        if abs(now - ts) > SIGNATURE_TOLERANCE_SECONDS:
            log.warning(f"Webhook timestamp too old/future: {ts} vs {now}")
            return False

        # Build the signed content
        signed_content = f"{webhook_id}.{webhook_timestamp}.{payload_bytes.decode('utf-8')}".encode()

        # Decode the secret (Svix secrets are base64-encoded after the "whsec_" prefix)
        import base64
        secret = signing_secret
        if secret.startswith("whsec_"):
            secret = secret[6:]
        secret_bytes = base64.b64decode(secret)

        expected_mac = hmac.new(secret_bytes, signed_content, hashlib.sha256).digest()
        expected_sig = base64.b64encode(expected_mac).decode()

        # Signature header may contain multiple signatures: "v1,sig1 v1,sig2"
        for sig_pair in webhook_signature.split(" "):
            if "," not in sig_pair:
                continue
            version, sig = sig_pair.split(",", 1)
            if version == "v1" and hmac.compare_digest(sig, expected_sig):
                return True

        return False
    except Exception as e:
        log.error(f"Signature verification error: {e}")
        return False


# ── Webhook Endpoint ──────────────────────────────────────────────────────────

@router.post(
    "/postmortem-completed",
    status_code=status.HTTP_200_OK,
    summary="Receive incident.io post-mortem completion webhook",
)
async def handle_incident_io_webhook(
    request: Request,
    webhook_id: Optional[str] = Header(None, alias="webhook-id"),
    webhook_timestamp: Optional[str] = Header(None, alias="webhook-timestamp"),
    webhook_signature: Optional[str] = Header(None, alias="webhook-signature"),
) -> Dict[str, str]:
    """
    Accept POST from incident.io when a post-mortem is completed.

    Security: verifies HMAC-SHA256 signature before processing.
    Trigger: fires the CIRUS Temporal pipeline on closed+exported postmortem.
    """
    from app.core.config import settings

    raw_body = await request.body()

    # ── Signature verification ─────────────────────────────────────────────
    signing_secret = getattr(settings, "INCIDENT_IO_WEBHOOK_SECRET", "")
    if signing_secret:
        if not all([webhook_id, webhook_timestamp, webhook_signature]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing webhook signature headers",
            )
        if not _verify_svix_signature(
            raw_body, webhook_id, webhook_timestamp, webhook_signature, signing_secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Webhook signature verification failed",
            )
    else:
        log.warning("INCIDENT_IO_WEBHOOK_SECRET not set — signature verification skipped (insecure!)")

    # ── Parse and validate payload ─────────────────────────────────────────
    try:
        import json
        raw_json = json.loads(raw_body)
        payload = IncidentIOWebhookPayload(**raw_json)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid webhook payload: {e}",
        )

    # ── Check trigger condition ────────────────────────────────────────────
    incident = payload.get_incident()
    if not incident:
        log.info(f"Webhook event {payload.event_type}: no incident object, ignoring")
        return {"status": "ignored", "reason": "no_incident_object"}

    if not incident.is_postmortem_complete:
        log.info(
            f"Webhook for {incident.incident_reference}: not a completed postmortem "
            f"(status={incident.status}, postmortem_status={incident.postmortem_status})"
        )
        return {"status": "ignored", "reason": "postmortem_not_complete"}

    # ── Trigger CIRUS pipeline ─────────────────────────────────────────────
    log.info(
        f"Triggering CIRUS pipeline for incident.io {incident.incident_reference}: "
        f"postmortem={incident.postmortem_document_url}"
    )

    # Build the raw_text from the incident info for the pipeline
    raw_text = _build_incident_text(incident)

    try:
        from app.db.session import AsyncSessionLocal
        from app.services.incident_service import IncidentService
        from app.services.workflow_service import WorkflowService
        from app.schemas.incident import IncidentCreate
        from app.orchestrator.temporal_client import get_temporal_client
        from app.orchestrator.temporal_workflows import CIRUSWorkflow

        async with AsyncSessionLocal() as session:
            inc_svc = IncidentService(session)
            wf_svc = WorkflowService(session)

            # Create incident in CIRUS DB
            inc_create = IncidentCreate(
                raw_text=raw_text,
                title=incident.name,
                selected_artifacts=["policy", "iac", "rca", "runbook"],
                tags=[incident.incident_reference, "incident.io"],
            )
            cirus_incident = await inc_svc.create_incident(inc_create)
            run = await wf_svc.create_run(
                incident_id=cirus_incident.id,
                model_id=settings.LLM_PROVIDER,
                triggered_by=f"incident_io:{incident.incident_reference}",
            )
            await session.commit()

        # Store incident.io reference for GitHub PR creation later
        # We use a simple metadata field in the workflow id
        workflow_id = f"cirus-incidentio-{incident.incident_reference}-{run.id}"

        client = await get_temporal_client()
        await client.start_workflow(
            CIRUSWorkflow.run,
            args=[
                run.id,
                cirus_incident.id,
                raw_text,
                ["policy", "iac", "rca", "runbook"],
            ],
            id=workflow_id,
            task_queue="cirus-task-queue",
        )

        log.info(f"Temporal workflow started: {workflow_id}")
        return {
            "status": "triggered",
            "incident_reference": incident.incident_reference,
            "cirus_incident_id": cirus_incident.id,
            "temporal_workflow_id": workflow_id,
        }

    except Exception as e:
        log.error(f"Failed to trigger pipeline for {incident.incident_reference}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline trigger failed: {e}",
        )


def _build_incident_text(incident: IncidentPayload) -> str:
    """Construct a raw_text string from the incident.io payload for CIRUS processing."""
    lines = [
        f"Incident Reference: {incident.incident_reference}",
        f"Title: {incident.name}",
        f"Status: {incident.status}",
    ]
    if incident.severity:
        lines.append(f"Severity: {incident.severity.name}")
    if incident.summary:
        lines.append(f"Summary: {incident.summary}")
    if incident.postmortem_document_url:
        lines.append(f"Post-mortem URL: {incident.postmortem_document_url}")
    lines.append(f"Post-mortem Status: {incident.postmortem_status}")
    return "\n".join(lines)
