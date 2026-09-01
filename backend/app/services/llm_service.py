"""CIRUS — Service: LLM service supporting multiple providers.

Provides OpenAI-compatible API integration for incident normalization and artifact generation.
Supports Featherless, Groq, OpenAI, and Anthropic providers.

LLMService   — used by CIRUSPipeline and ArtifactService (real Groq/Featherless calls)
LLMProviderService — legacy helper used by the older run_workflow orchestrator
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import httpx
import openai
from pydantic import BaseModel, Field

from app.core.config import settings

log = logging.getLogger(__name__)


# ── Shared schema ─────────────────────────────────────────────────────────────

class LLMMessage(BaseModel):
    role: str
    content: str


class LLMResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    content: str
    tokens_used: int = 0
    model_id: str = ""


# ── Pipeline LLM service (used by CIRUSPipeline & ArtifactService) ────────────

class LLMService:
    """Real LLM service backed by the provider configured in settings.

    Supports: groq | featherless | openai
    Uses the OpenAI-compatible chat completions endpoint.
    """

    def __init__(self) -> None:
        provider = settings.LLM_PROVIDER

        if provider == "featherless":
            if not settings.FEATHERLESS_API_KEY:
                raise ValueError("FEATHERLESS_API_KEY is not set")
            self._client = openai.AsyncOpenAI(
                api_key=settings.FEATHERLESS_API_KEY,
                base_url=settings.FEATHERLESS_BASE_URL,
            )
            self._model = settings.FEATHERLESS_MODEL

        elif provider == "groq":
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY is not set")
            self._client = openai.AsyncOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
            )
            self._model = settings.GROQ_MODEL

        elif provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is not set")
            self._client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
            )
            self._model = settings.OPENAI_MODEL

        elif provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY is not set")
            self._client = None  # Anthropic is called through httpx in complete().
            self._model = settings.ANTHROPIC_MODEL

        elif provider == "mock":
            self._client = None  # type: ignore[assignment]
            self._model = "mock"

        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

        self._provider = provider
        log.info("LLMService initialised", extra={"provider": provider, "model": self._model})

    async def complete(
        self,
        messages: List[LLMMessage],
        system: str = "",
    ) -> LLMResponse:
        """Send a chat completion request and return a structured response."""

        if self._provider == "mock":
            return LLMResponse(content="{}", tokens_used=0, model_id="mock")

        if self._provider == "anthropic":
            headers = {
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            user_content = "\n\n".join(m.content for m in messages)
            payload = {
                "model": self._model,
                "system": system,
                "messages": [{"role": "user", "content": user_content}],
                "temperature": settings.LLM_TEMPERATURE,
                "max_tokens": settings.LLM_MAX_TOKENS,
            }
            async with httpx.AsyncClient(timeout=settings.PIPELINE_TIMEOUT_SECONDS) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
            data = resp.json()
            content_parts = data.get("content", [])
            content = "".join(
                part.get("text", "") for part in content_parts if part.get("type") == "text"
            ) or "{}"
            usage = data.get("usage", {})
            tokens = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
            return LLMResponse(content=content, tokens_used=tokens, model_id=self._model)

        oai_messages = []
        if system:
            oai_messages.append({"role": "system", "content": system})
        for m in messages:
            oai_messages.append({"role": m.role, "content": m.content})

        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=oai_messages,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            tokens = resp.usage.total_tokens if resp.usage else 0
            return LLMResponse(content=content, tokens_used=tokens, model_id=self._model)

        except openai.APIError as exc:
            # Handle provider errors gracefully; if the model is not available
            # fall back to a harmless mock response so the pipeline can continue
            msg = str(exc)
            log.error("LLM API error", extra={"error": msg})
            if "model" in msg and ("does not exist" in msg or "model_not_found" in msg or "not found" in msg):
                log.warning("LLM model not found — falling back to mock response", extra={"model": self._model})
                return LLMResponse(content="{}", tokens_used=0, model_id=self._model)
            raise
        except Exception as exc:
            log.error("LLM unexpected error", extra={"error": str(exc)})
            # Fallback to a mock response for unexpected errors in development
            if settings.ENVIRONMENT == "development" or settings.MODE == "mock":
                log.warning("Unexpected LLM error — returning mock response in development/mode=mock")
                return LLMResponse(content="{}", tokens_used=0, model_id=self._model)
            raise


# ── Legacy service (used by run_workflow in orchestrator.py) ──────────────────

class IncidentData(BaseModel):
    """Pydantic model for normalized incident data."""
    title: str = Field(..., description="Brief title of the incident")
    provider: str = Field(..., description="Cloud provider (e.g., AWS, GCP, Azure)")
    severity: str = Field(..., description="Severity level (e.g., critical, high, medium, low)")
    symptoms: str = Field(..., description="Observed symptoms and impact")
    root_cause: str = Field(..., description="Root cause analysis")


class LLMProviderService:
    """Legacy LLM service used by the run_workflow orchestrator."""

    def __init__(self) -> None:
        provider = settings.LLM_PROVIDER
        self.provider = provider

        if provider == "featherless":
            api_key = settings.FEATHERLESS_API_KEY
            base_url = settings.FEATHERLESS_BASE_URL
            model = settings.FEATHERLESS_MODEL
            if not api_key:
                raise ValueError("FEATHERLESS_API_KEY is not set")
        elif provider == "groq":
            api_key = settings.GROQ_API_KEY
            base_url = settings.GROQ_BASE_URL
            model = settings.GROQ_MODEL
            if not api_key:
                raise ValueError("GROQ_API_KEY is not set")
        elif provider == "openai":
            api_key = settings.OPENAI_API_KEY
            base_url = "https://api.openai.com/v1"
            model = settings.OPENAI_MODEL
            if not api_key:
                raise ValueError("OPENAI_API_KEY is not set")
        elif provider == "mock":
            self.client = None  # type: ignore[assignment]
            self.model = "mock"
            return
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self.client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        log.info("LLMProviderService initialised with provider: %s", provider)

    async def normalize_incident(self, raw_text: str) -> Dict[str, Any]:
        if self.provider == "mock":
            return {
                "title": "Mock Incident",
                "provider": "AWS",
                "severity": "medium",
                "symptoms": "Mock symptoms",
                "root_cause": "Mock root cause",
            }

        system_prompt = (
            "You are an expert Cloud SRE. Analyse incident reports and extract structured "
            "information in JSON format with keys: title, provider, severity, symptoms, root_cause. "
            "Respond ONLY with valid JSON."
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": raw_text},
                ],
                response_format={"type": "json_object"},
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            validated = IncidentData(**parsed)
            return validated.model_dump()
        except openai.APIError as exc:
            msg = str(exc)
            log.error("LLMProviderService API error during normalization", extra={"error": msg})
            if "model" in msg and ("does not exist" in msg or "model_not_found" in msg or "not found" in msg):
                log.warning("LLM model not found in provider service — returning mock normalized data")
                return {
                    "title": "Fallback Incident",
                    "provider": "unknown",
                    "severity": "medium",
                    "symptoms": "(model unavailable)",
                    "root_cause": "(model unavailable)",
                }
            raise

    async def generate_artifacts(self, context: Dict[str, Any]) -> Dict[str, str]:
        if self.provider == "mock":
            return {"terraform": "# mock", "policy": "# mock", "runbook": "# mock"}

        system_prompt = (
            "You are an expert Cloud Infrastructure Engineer. Generate infrastructure artifacts "
            "based on incident context. Return JSON with keys: terraform, policy, runbook."
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Incident context:\n{json.dumps(context, indent=2)}"},
                ],
                response_format={"type": "json_object"},
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            return {
                "terraform": parsed.get("terraform", ""),
                "policy": parsed.get("policy", ""),
                "runbook": parsed.get("runbook", ""),
            }
        except openai.APIError as exc:
            msg = str(exc)
            log.error("LLMProviderService API error during artifact generation", extra={"error": msg})
            log.warning("Returning empty artifacts due to LLM provider error")
            return {"terraform": "", "policy": "", "runbook": ""}


# Backward-compat alias
FeatherlessService = LLMProviderService
