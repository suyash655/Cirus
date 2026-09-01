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
    ) -> dict:
        """Generate a single artifact via LLM and persist it."""
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
                    content = {"code": "package cirus\n\n# mock policy to block insecure-s3"}
                elif artifact_type == "iac":
                    content = {"fullPatch": "- resource \"aws_s3_bucket\" \"fixed\" {\n  # mock patch\n}\n"}
                elif artifact_type == "runbook":
                    content = {"steps": [{"id": 1, "title": "Investigate", "description": "Check S3 buckets."}]} 
                elif artifact_type == "alerts":
                    content = {"rules": [{"name": "HighErrorRate", "expression": "sum(errors) > 100"}]}
                elif artifact_type == "rca":
                    content = {"executiveSummary": "Mock RCA: root cause identified as infrastructure damage.", "details": "Mock details."}
                else:
                    content = {"content": "mock"}
            else:
                raise ArtifactGenerationError(artifact_type, "LLM returned empty or invalid JSON.")

        # Ensure type field is set
        content["type"] = artifact_type

        artifact = await self._repo.upsert(
            incident_id=incident_id,
            artifact_type=ArtifactType(artifact_type),
            content=content,
            model_id=response.model_id,
            tokens_used=response.tokens_used,
        )
        log.info("artifact generated", incident_id=incident_id, type=artifact_type, version=artifact.version)
        return content

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
        content = await self.generate_artifact(
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
