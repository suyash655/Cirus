#!/usr/bin/env python
"""CIRUS — Temporal Worker entry point.

Start the Temporal worker with:

    cd backend
    python run_worker.py

Or from the project root:

    python backend/run_worker.py

Prerequisites:
  1. Temporal server must be running. Start it with:
         ./temporal server start-dev
     (The temporal.exe binary is already in the project root.)

  2. The CIRUS backend virtual environment must be active.

  3. Set TEMPORAL_ENABLED=true in backend/.env (already done if you followed setup).

The worker registers all activities and the CIRUSWorkflow, then listens
on the 'cirus-task-queue' task queue (configurable via TEMPORAL_TASK_QUEUE).

When CIRUS receives a new incident it will automatically dispatch to this
worker via Temporal for durable, retryable workflow execution. If the worker
is not running, the API falls back to FastAPI BackgroundTasks automatically.
"""
import asyncio
import logging
import os
import sys

# Ensure the backend directory is on sys.path when run directly
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Ensure mlops (eval gate) is importable
_project_root = os.path.dirname(_backend_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from temporalio.client import Client
from temporalio.worker import Worker

from app.core.config import settings
from app.core.logging import configure_logging
from app.orchestrator.temporal_workflows import CIRUSWorkflow
from app.orchestrator.temporal_activities import (
    normalize_incident,
    classify_root_cause,
    enrich_context,
    generate_artifacts,
    score_risk,
    extract_citations,
    update_incident_status,
    update_run_status,
)

log = logging.getLogger(__name__)


def _import_optional_activities():
    """Import optional activities that may fail if deps are missing."""
    activities = []

    try:
        from mlops.evaluation.eval_gate_activity import run_eval_gate
        activities.append(run_eval_gate)
        log.info("eval_gate activity loaded")
    except ImportError as e:
        log.warning("eval_gate activity not available (deepeval missing?)", error=str(e))

    try:
        from app.services.github_pr_activity import open_github_pr
        activities.append(open_github_pr)
        log.info("open_github_pr activity loaded")
    except ImportError as e:
        log.warning("open_github_pr activity not available", error=str(e))

    return activities


async def main() -> None:
    configure_logging()

    host = settings.TEMPORAL_HOST
    namespace = settings.TEMPORAL_NAMESPACE
    task_queue = settings.TEMPORAL_TASK_QUEUE

    log.info(
        "CIRUS Temporal Worker starting",
        host=host,
        namespace=namespace,
        task_queue=task_queue,
    )

    try:
        client = await Client.connect(host, namespace=namespace)
    except Exception as e:
        log.error(
            "Failed to connect to Temporal Server. "
            "Make sure it is running: ./temporal server start-dev",
            host=host,
            error=str(e),
        )
        sys.exit(1)

    core_activities = [
        normalize_incident,
        classify_root_cause,
        enrich_context,
        generate_artifacts,
        score_risk,
        extract_citations,
        update_incident_status,
        update_run_status,
    ]
    optional_activities = _import_optional_activities()
    all_activities = core_activities + optional_activities

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[CIRUSWorkflow],
        activities=all_activities,
    )

    log.info(
        "Worker registered",
        workflows=["CIRUSWorkflow"],
        activities=[fn.__name__ for fn in all_activities],
        task_queue=task_queue,
    )
    print(f"\n✅ CIRUS Temporal Worker running on task queue '{task_queue}'")
    print(f"   Connected to: {host} (namespace: {namespace})")
    print("   Press Ctrl+C to stop.\n")

    await worker.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹  Worker stopped.")
