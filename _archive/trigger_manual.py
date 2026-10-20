import asyncio
import sys

# Add backend to path
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal
from app.models.incident import Incident
from app.models.run import WorkflowRun
from app.orchestrator.temporal_client import get_temporal_client
from app.orchestrator.temporal_workflows import CIRUSWorkflow
from sqlalchemy import select

async def trigger(incident_id: str):
    async with AsyncSessionLocal() as session:
        # Get incident
        inc = await session.execute(select(Incident).where(Incident.id == incident_id))
        incident = inc.scalar_one_or_none()
        
        # Get run
        run_res = await session.execute(select(WorkflowRun).where(WorkflowRun.incident_id == incident_id))
        run = run_res.scalars().first()

        if not incident or not run:
            print(f"Not found. Incident: {incident}, Run: {run}")
            return
            
        print(f"Triggering for {incident_id} and run {run.id}")
        client = await get_temporal_client()
        await client.start_workflow(
            CIRUSWorkflow.run,
            args=[
                run.id,
                incident.id,
                incident.raw_text,
                ["policy", "iac", "rca", "runbook"],
            ],
            id=f"cirus-pipeline-{incident.id}-{run.id}",
            task_queue="cirus-task-queue",
        )
        print("Workflow started!")

if __name__ == "__main__":
    asyncio.run(trigger("inc-454b115c13cf"))
