"""CIRUS — Service: Artifact generation and retrieval."""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ArtifactGenerationError
from app.core.logging import get_logger
from app.models.artifact import ArtifactType
from app.repositories.artifact_repository import ArtifactRepository
from app.schemas.artifact import ArtifactRead, ArtifactSetRead
from app.services.llm_service import LLMMessage, LLMService
from app.core.config import settings
from app.services.prompt_service import PromptService
from app.utils.json_repair import parse_llm_json
from app.utils.ids import artifact_id

log = get_logger(__name__)

_ARTIFACT_PROMPT_MAP = {
    "rca": "rca_artifact_prompt",
    "policy": "policy_artifact_prompt",
    "iac": "iac_artifact_prompt",
    "alerts": "alerts_artifact_prompt",
    "runbook": "runbook_artifact_prompt",
    "regression": "regression_artifact_prompt",
}


class ArtifactService:
    def __init__(self, db: AsyncSession, llm: LLMService) -> None:
        self._repo = ArtifactRepository(db)
        self._llm = llm
        self._prompts = PromptService()

    async def generate_artifact(
        self,
        incident_id: str,
        artifact_type: str,
        raw_text: str,
        root_cause: dict,
        extraction: dict,
    ) -> tuple:
        """Generate a single artifact via LLM, persist it, and return (content, raw_code).

        raw_code is the code string to hand to the syntax validators:
          - policy  -> content['code']       (Rego)
          - iac     -> content.get('full_patch') or content.get('fullPatch')  (Terraform HCL)
          - others  -> '' (no AST validator applies)
        """
        prompt_method = _ARTIFACT_PROMPT_MAP.get(artifact_type)
        if not prompt_method:
            raise ArtifactGenerationError(artifact_type, f"Unknown artifact type: {artifact_type}")

        prompt_fn = getattr(self._prompts, prompt_method)
        # Different methods take different args
        if artifact_type == "rca":
            user_prompt = prompt_fn(raw_text, root_cause, extraction)
        else:
            user_prompt = prompt_fn(root_cause, extraction)

        try:
            response = await self._llm.complete(
                messages=[LLMMessage(role="user", content=user_prompt)],
                system=self._prompts.system_prompt,
            )
        except Exception as e:
            raise ArtifactGenerationError(artifact_type, str(e))

        content = parse_llm_json(response.content, default={})
        # If LLM returned empty content, provide a safe mock fallback in
        # development or when running with MODE=mock so the pipeline produces
        # usable artifacts for local testing.
        if not content:
            if settings.ENVIRONMENT == "development" or settings.MODE == "mock":
                # Provide simple mock content tailored to artifact type
                if artifact_type == "policy":
                    content = {"code": 'package cirus.guardrail\n\nimport rego.v1\n\n# Mock: deny any S3 bucket that is public\ndefault deny := false\n\ndeny if {\n    input.resource == "aws_s3_bucket"\n    input.public_access == true\n}\n'}
                elif artifact_type == "iac":
                    content = {"full_patch": 'resource "aws_s3_bucket_public_access_block" "demo_remediation" {\n  bucket                  = aws_s3_bucket.example.id\n  block_public_acls       = true\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n}\n', "fullPatch": "# see full_patch"}
                elif artifact_type == "runbook":
                    content = {"steps": [{"id": 1, "title": "Investigate", "description": "Check S3 buckets for public access."}]}
                elif artifact_type == "alerts":
                    content = {"rules": [{"name": "PublicS3BucketDetected", "expression": "aws_s3_public_access_enabled > 0", "severity": "critical"}]}
                elif artifact_type == "rca":
                    content = {"executiveSummary": "Mock RCA: S3 bucket was inadvertently set to public.", "details": "Root cause: missing public access block on bucket creation."}
                else:
                    content = {"content": "mock"}
            else:
                raise ArtifactGenerationError(artifact_type, "LLM returned empty or invalid JSON.")

        # Ensure type field is set
        content["type"] = artifact_type

        # Extract the raw validatable code string for the validator stage.
        # policy -> Rego code, iac -> Terraform HCL, everything else -> empty.
        raw_code = ""
        if artifact_type == "policy":
            raw_code = content.get("code", "")
        elif artifact_type == "iac":
            raw_code = content.get("full_patch") or content.get("fullPatch") or ""

        artifact = await self._repo.upsert(
            incident_id=incident_id,
            artifact_type=ArtifactType(artifact_type),
            content=content,
            model_id=response.model_id,
            tokens_used=response.tokens_used,
        )
        log.info("artifact generated", incident_id=incident_id, type=artifact_type, version=artifact.version)
        return content, raw_code

    async def get_artifact_set(self, incident_id: str) -> ArtifactSetRead:
        artifacts = await self._repo.list_by_incident(incident_id)
        result: Dict[str, Optional[ArtifactRead]] = {
            "rca": None, "policy": None, "iac": None,
            "alerts": None, "runbook": None, "regression": None,
        }
        for a in artifacts:
            content = parse_llm_json(a.content, default={})
            result[a.artifact_type.value] = ArtifactRead(
                id=a.id,
                incident_id=a.incident_id,
                artifact_type=a.artifact_type.value,
                content=content,
                version=a.version,
                model_id=a.model_id,
                tokens_used=a.tokens_used,
            )
        return ArtifactSetRead(**result)

    async def regenerate(
        self,
        incident_id: str,
        artifact_type: str,
        raw_text: str,
        root_cause: dict,
        extraction: dict,
    ) -> ArtifactRead:
        content, _raw_code = await self.generate_artifact(
            incident_id=incident_id,
            artifact_type=artifact_type,
            raw_text=raw_text,
            root_cause=root_cause,
            extraction=extraction,
        )
        artifact = await self._repo.get_by_type(incident_id, ArtifactType(artifact_type))
        return ArtifactRead(
            id=artifact.id,
            incident_id=incident_id,
            artifact_type=artifact_type,
            content=content,
            version=artifact.version,
            model_id=artifact.model_id,
            tokens_used=artifact.tokens_used,
        )
