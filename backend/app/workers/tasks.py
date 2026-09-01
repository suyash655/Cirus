"""CIRUS — Workers: Temporal Worker entry point.

Run this script directly to start the Temporal Worker:
    python -m app.workers.tasks
"""
import asyncio
import logging
import sys
from temporalio.client import Client
from temporalio.worker import Worker

# Update sys.path if needed depending on how it's invoked, 
# but python -m app.workers.tasks should have the right path.
import os
import sys
# Add the project root to sys.path so 'mlops' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from app.core.config import settings
from app.core.logging import configure_logging
from app.orchestrator.temporal_workflows import CIRUSWorkflow
from app.orchestrator.temporal_activities import (
    normalize_incident, classify_root_cause, enrich_context,
    generate_artifacts, score_risk,
    extract_citations, update_incident_status
)
from mlops.evaluation.eval_gate_activity import run_eval_gate
from app.services.github_pr_activity import open_github_pr

log = logging.getLogger(__name__)

async def main():
    configure_logging()
    log.info("Starting Temporal Worker...")

    try:
        client = await Client.connect("localhost:7233")
    except Exception as e:
        log.error(f"Failed to connect to Temporal Server: {e}")
        return

    worker = Worker(
        client,
        task_queue="cirus-task-queue",
        workflows=[CIRUSWorkflow],
        activities=[
            normalize_incident, classify_root_cause, enrich_context,
            generate_artifacts, run_eval_gate, score_risk,
            extract_citations, update_incident_status,
            open_github_pr,
        ],
    )
    
    log.info("Worker started on task queue 'cirus-task-queue'")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
