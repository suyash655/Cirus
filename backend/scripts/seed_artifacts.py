#!/usr/bin/env python
"""Seed deterministic artifacts for local testing.

Usage: python backend/scripts/seed_artifacts.py [incident_id]
"""
import asyncio
import sys

from app.db.session import AsyncSessionLocal
from app.repositories.artifact_repository import ArtifactRepository
# Ensure ORM mappers are registered
import app.models.incident  # noqa: F401
import app.models.run  # ensure WorkflowRun mapper is registered
import app.models.citation  # noqa: F401
from app.models.artifact import ArtifactType


async def main(incident_id: str = "inc-8b28e3bbb556") -> None:
    async with AsyncSessionLocal() as session:
        repo = ArtifactRepository(session)

        artifacts = {
            "policy": {
                "code": "package cirus\n\n# seeded policy to deny public S3\ndeny[msg] { msg := \"bucket public\" }",
            },
            "iac": {
                "fullPatch": 'resource "aws_s3_bucket" "fixed" { acl = "private" }\n',
            },
            "alerts": {
                "rules": [
                    {"name": "HighErrorRate", "expression": "sum(errors) > 100", "severity": "critical"}
                ]
            },
            "rca": {
                "executiveSummary": "Seeded RCA: misconfigured S3 bucket allowed public writes.",
                "details": "Bucket policy allowed public write access causing data loss.",
            },
            "runbook": {
                "steps": [
                    {"id": 1, "title": "Investigate", "description": "Check S3 bucket ACLs and server access logs."},
                    {"id": 2, "title": "Mitigate", "description": "Set ACL to private and rotate keys."},
                ]
            },
        }

        for atype, content in artifacts.items():
            art = await repo.upsert(
                incident_id=incident_id,
                artifact_type=ArtifactType(atype),
                content=content,
                model_id="seeded",
                tokens_used=0,
            )
            print(f"Upserted {atype}: {art.id} (version={art.version})")


if __name__ == "__main__":
    incident = sys.argv[1] if len(sys.argv) > 1 else "inc-8b28e3bbb556"
    asyncio.run(main(incident))
