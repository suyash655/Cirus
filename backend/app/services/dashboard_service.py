"""CIRUS — Service: Dashboard statistics aggregation."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact, ArtifactType
from app.models.incident import Incident, IncidentStatus
from app.models.run import WorkflowRun, WorkflowRunStatus
from app.schemas.dashboard import ArtifactSummary, DashboardStats, RiskTrendPoint


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_stats(self) -> DashboardStats:
        # ── Total incidents ───────────────────────────────────────────────────
        total_result = await self._db.execute(select(func.count(Incident.id)))
        total_incidents = total_result.scalar_one() or 0

        # ── Ready (awaiting approval) ─────────────────────────────────────────
        ready_result = await self._db.execute(
            select(func.count(Incident.id)).where(
                Incident.status == IncidentStatus.ready
            )
        )
        awaiting_approval = ready_result.scalar_one() or 0

        # ── Artifact counts by type ───────────────────────────────────────────
        art_result = await self._db.execute(
            select(Artifact.artifact_type, func.count(Artifact.id)).group_by(
                Artifact.artifact_type
            )
        )
        art_counts: dict = {row[0]: row[1] for row in art_result.all()}
        guardrails_generated = sum(art_counts.values())

        summary = ArtifactSummary(
            policies=art_counts.get(ArtifactType.policy, 0),
            iac_patches=art_counts.get(ArtifactType.iac, 0),
            alerts=art_counts.get(ArtifactType.alerts, 0),
            runbooks=art_counts.get(ArtifactType.runbook, 0),
            regression_tests=art_counts.get(ArtifactType.regression, 0),
        )

        # ── Real risk trend (last 7 days from completed runs) ─────────────────
        risk_trend, avg_risk_reduction = await self._build_real_trend()

        # ── Mean Time to Guardrail (hours) ────────────────────────────────────
        mttg_hours = await self._compute_mttg()

        return DashboardStats(
            total_incidents=total_incidents,
            guardrails_generated=guardrails_generated,
            avg_risk_reduction=avg_risk_reduction,
            awaiting_approval=awaiting_approval,
            artifact_summary=summary,
            risk_trend=risk_trend,
            mttg_hours=mttg_hours,
        )

    async def _build_real_trend(self) -> tuple[List[RiskTrendPoint], float]:
        """
        Query completed WorkflowRuns from the last 7 days.
        Extract risk_score.before_remediation and .after_remediation from the
        stages JSON blob, average them per calendar day (UTC).
        Falls back to a mock trend if no completed runs exist yet.
        """
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=7)

        result = await self._db.execute(
            select(WorkflowRun.stages, WorkflowRun.completed_at)
            .where(WorkflowRun.status == WorkflowRunStatus.completed)
            .where(WorkflowRun.completed_at >= cutoff)
            .order_by(WorkflowRun.completed_at.asc())
        )
        rows = result.all()

        # Build day-bucket accumulators: { "Sep 01": [before, after, count] }
        buckets: dict[str, list] = {}
        all_deltas: list[float] = []

        for stages_json, completed_at in rows:
            if not stages_json or not completed_at:
                continue
            try:
                stages = json.loads(stages_json)
            except (json.JSONDecodeError, TypeError):
                continue

            # Find the risk-scoring stage output
            risk_stage = next(
                (s for s in stages if isinstance(s, dict) and s.get("id") == "risk-scoring"),
                None,
            )
            if not risk_stage:
                continue

            output = risk_stage.get("output") or {}
            data = output.get("data") or {}
            before = data.get("before_remediation")
            after = data.get("after_remediation")

            if before is None or after is None:
                # Try flat output keys as fallback
                before = output.get("before_remediation")
                after = output.get("after_remediation") or output.get("overall")

            if before is None or after is None:
                continue

            try:
                before = float(before)
                after = float(after)
            except (ValueError, TypeError):
                continue

            # Make completed_at timezone-aware if needed
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)

            day_label = completed_at.strftime("%b %d")
            if day_label not in buckets:
                buckets[day_label] = [0.0, 0.0, 0]
            buckets[day_label][0] += before
            buckets[day_label][1] += after
            buckets[day_label][2] += 1
            all_deltas.append(before - after)

        trend: List[RiskTrendPoint] = [
            RiskTrendPoint(
                date=day,
                avg_risk_before=round(totals[0] / totals[2], 1),
                avg_risk_after=round(totals[1] / totals[2], 1),
            )
            for day, totals in buckets.items()
            if totals[2] > 0
        ]

        avg_reduction = round(sum(all_deltas) / len(all_deltas), 1) if all_deltas else 0.0

        # Fall back to mock trend when no real data exists yet
        if not trend:
            trend = self._build_mock_trend()

        return trend, avg_reduction

    async def _compute_mttg(self) -> float:
        """
        Mean Time to Guardrail: average hours from incident.created_at to
        run.completed_at for all completed runs that have a non-null
        completed_at. Returns 0.0 if no completed runs exist yet.
        """
        result = await self._db.execute(
            select(Incident.created_at, WorkflowRun.completed_at)
            .join(WorkflowRun, WorkflowRun.incident_id == Incident.id)
            .where(WorkflowRun.status == WorkflowRunStatus.completed)
            .where(WorkflowRun.completed_at.is_not(None))
        )
        rows = result.all()

        if not rows:
            return 0.0

        durations_hours: list[float] = []
        for created_at, completed_at in rows:
            if created_at is None or completed_at is None:
                continue
            # Normalise to UTC-aware
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            delta = (completed_at - created_at).total_seconds()
            if delta >= 0:
                durations_hours.append(delta / 3600)

        if not durations_hours:
            return 0.0

        return round(sum(durations_hours) / len(durations_hours), 1)

    def _build_mock_trend(self) -> list[RiskTrendPoint]:
        """Fallback trend used when no completed runs exist yet."""
        base = datetime.now(tz=timezone.utc)
        return [
            RiskTrendPoint(
                date=(base - timedelta(days=6 - i)).strftime("%b %d"),
                avg_risk_before=75.0 - i * 2,
                avg_risk_after=45.0 - i * 3,
            )
            for i in range(7)
        ]
