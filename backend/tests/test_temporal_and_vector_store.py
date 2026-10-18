"""CIRUS — Unit tests for Temporal Orchestration & ChromaDB Vector Store.

Tests:
  - Temporal settings and client fallback
  - Temporal worker activities registration
  - Vector store graceful disabled state
  - Vector store mock upsert, query, delete, and similarity math
  - API endpoint: GET /api/v1/incidents/{id}/similar
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
settings.ALLOWED_API_KEYS = "test-key-123"
settings.MODE = "mock"
settings.ENVIRONMENT = "development"

from app.main import app
from app.db.base import Base
from app.db.session import engine
from app.orchestrator.temporal_client import get_temporal_client, reset_temporal_client
from app.services import vector_store

API_KEY = "test-key-123"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture(autouse=True)
async def init_test_tables():
    """Ensure all database tables exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


# ── Feature 1: Temporal Tests ─────────────────────────────────────────────────

class TestTemporalIntegration:
    def test_temporal_settings_defaults(self):
        """Settings should contain the Temporal configuration fields."""
        assert hasattr(settings, "TEMPORAL_ENABLED")
        assert hasattr(settings, "TEMPORAL_HOST")
        assert hasattr(settings, "TEMPORAL_NAMESPACE")
        assert hasattr(settings, "TEMPORAL_TASK_QUEUE")
        assert settings.TEMPORAL_TASK_QUEUE == "cirus-task-queue"

    async def test_temporal_client_connection_failure_handled(self):
        """Connecting to an unreachable Temporal host raises without hanging."""
        reset_temporal_client()
        with patch.object(settings, "TEMPORAL_HOST", "localhost:9999"):
            with pytest.raises(Exception):
                await get_temporal_client()
        reset_temporal_client()

    def test_run_worker_activity_imports(self):
        """Worker core activities must be importable."""
        from app.orchestrator.temporal_activities import (
            classify_root_cause,
            enrich_context,
            extract_citations,
            generate_artifacts,
            normalize_incident,
            score_risk,
            update_incident_status,
            update_run_status,
        )
        assert callable(normalize_incident)
        assert callable(classify_root_cause)
        assert callable(enrich_context)
        assert callable(generate_artifacts)
        assert callable(score_risk)
        assert callable(extract_citations)
        assert callable(update_incident_status)
        assert callable(update_run_status)


# ── Feature 2: Vector Store Tests ─────────────────────────────────────────────

class TestVectorStoreService:
    async def test_vector_store_noop_when_disabled(self):
        """When VECTOR_STORE_ENABLED is False, functions return immediately."""
        with patch.object(settings, "VECTOR_STORE_ENABLED", False):
            # None of these should call _get_collection or raise
            await vector_store.upsert_incident("inc-test", "raw text")
            results = await vector_store.query_similar("query text")
            assert results == []
            await vector_store.delete_incident("inc-test")
            count = await vector_store.vector_store_count()
            assert count == 0

    async def test_query_similar_with_mocked_collection(self):
        """Test query logic, score calculation, and exclude_id filtering."""
        mock_col = MagicMock()
        mock_col.count.return_value = 2
        mock_col.query.return_value = {
            "ids": [["inc-1", "inc-2"]],
            "documents": [["First incident text", "Second incident text"]],
            "metadatas": [[{"severity": "P1"}, {"severity": "P2"}]],
            "distances": [[0.2, 0.8]],  # L2 distances
        }

        with patch.object(settings, "VECTOR_STORE_ENABLED", True):
            with patch("app.services.vector_store._get_collection", return_value=mock_col):
                # Query without exclude
                hits = await vector_store.query_similar("test query", top_k=5)
                assert len(hits) == 2
                # similarity_pct = round(max(0.0, 1.0 - 0.2 / 2.0) * 100, 1) = 90.0
                assert hits[0]["incident_id"] == "inc-1"
                assert hits[0]["similarity_pct"] == 90.0
                # similarity_pct = round(max(0.0, 1.0 - 0.8 / 2.0) * 100, 1) = 60.0
                assert hits[1]["incident_id"] == "inc-2"
                assert hits[1]["similarity_pct"] == 60.0

                # Query with exclude_id
                hits_filtered = await vector_store.query_similar(
                    "test query", top_k=5, exclude_id="inc-1"
                )
                assert len(hits_filtered) == 1
                assert hits_filtered[0]["incident_id"] == "inc-2"


# ── Feature 2: /similar API Endpoint Test ─────────────────────────────────────

class TestSimilarIncidentsEndpoint:
    async def test_similar_endpoint_returns_200(self):
        """GET /api/v1/incidents/{id}/similar should return matching format."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create an incident first
            sample = {
                "raw_text": "Sample database latency spike incident on AWS RDS PostgreSQL",
                "severity": "P2",
                "provider": "AWS",
                "selectedArtifacts": ["rca"],
            }
            create_resp = await client.post("/api/v1/incidents/", json=sample, headers=HEADERS)
            assert create_resp.status_code == 201
            incident_id = create_resp.json()["id"]

            # 2. Query similar incidents endpoint
            mock_hits = [
                {
                    "incident_id": "inc-past-1",
                    "raw_text_snippet": "Past AWS RDS latency spike...",
                    "metadata": {"severity": "P2"},
                    "distance": 0.15,
                    "similarity_pct": 92.5,
                }
            ]
            with patch("app.services.vector_store.query_similar", new=AsyncMock(return_value=mock_hits)):
                resp = await client.get(
                    f"/api/v1/incidents/{incident_id}/similar?top_k=3",
                    headers=HEADERS,
                )
                assert resp.status_code == 200
                data = resp.json()
                assert data["incident_id"] == incident_id
                assert data["total"] == 1
                assert len(data["similar"]) == 1
                assert data["similar"][0]["incident_id"] == "inc-past-1"
                assert data["similar"][0]["similarity_pct"] == 92.5
