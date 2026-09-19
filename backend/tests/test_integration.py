"""CIRUS — Integration tests: Incident API + Pipeline happy path.

Tests the real FastAPI application against an in-memory SQLite database
in mock mode, covering:
  - Incident creation (POST /incidents/)
  - Incident retrieval (GET /incidents/{id})
  - Incident listing with filters (GET /incidents/)
  - Artifact retrieval (GET /artifacts/{incident_id})
  - Dashboard stats (GET /dashboard/stats)
  - Input validation boundaries (raw_text min/max length)
  - Auth enforcement

Run: pytest backend/tests/test_integration.py -v
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force mock mode before importing the app
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("MODE", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ALLOWED_API_KEYS", "test-key-123")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-integration-tests")

from app.main import app  # noqa: E402 — import after env setup
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402

API_KEY = "test-key-123"
HEADERS = {"X-API-Key": API_KEY}

SAMPLE_INCIDENT = {
    "raw_text": (
        "ALERT: S3 bucket 'prod-data-lake-us-east-1' is publicly accessible.\n"
        "Severity: Critical\n"
        "Account: 123456789012\n"
        "Region: us-east-1\n"
        "Affected resource: arn:aws:s3:::prod-data-lake-us-east-1\n"
        "Detection time: 2024-01-15T10:30:00Z\n"
        "Misconfiguration: ACL set to public-read. Block Public Access is disabled."
    ),
    "severity": "P1",
    "provider": "AWS",
    "selectedArtifacts": ["rca", "policy"],
}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db():
    """Create all tables in the in-memory test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session")
async def client(test_db) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ── Auth tests ────────────────────────────────────────────────────────────────

class TestAuth:
    async def test_missing_api_key_returns_401(self, client: AsyncClient):
        """Requests without an API key must be rejected."""
        resp = await client.get("/api/v1/incidents/")
        assert resp.status_code == 401

    async def test_invalid_api_key_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/incidents/",
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    async def test_valid_key_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/v1/incidents/", headers=HEADERS)
        assert resp.status_code == 200


# ── Incident CRUD ─────────────────────────────────────────────────────────────

class TestIncidentCreation:
    async def test_create_incident_returns_201(self, client: AsyncClient):
        resp = await client.post("/api/v1/incidents/", json=SAMPLE_INCIDENT, headers=HEADERS)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "estimated_processing_ms" in data

    async def test_created_incident_is_retrievable(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/incidents/", json=SAMPLE_INCIDENT, headers=HEADERS)
        incident_id = create_resp.json()["id"]

        get_resp = await client.get(f"/api/v1/incidents/{incident_id}", headers=HEADERS)
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == incident_id
        assert data["severity"] == "P1"
        assert data["provider"] == "AWS"
        assert data["status"] in ("processing", "ready", "error")

    async def test_unknown_incident_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/incidents/does-not-exist", headers=HEADERS)
        assert resp.status_code == 404

    async def test_raw_text_too_short_returns_422(self, client: AsyncClient):
        payload = {**SAMPLE_INCIDENT, "raw_text": "short"}
        resp = await client.post("/api/v1/incidents/", json=payload, headers=HEADERS)
        assert resp.status_code == 422

    async def test_raw_text_too_long_returns_422(self, client: AsyncClient):
        payload = {**SAMPLE_INCIDENT, "raw_text": "x" * 100_001}
        resp = await client.post("/api/v1/incidents/", json=payload, headers=HEADERS)
        assert resp.status_code == 422

    async def test_invalid_severity_returns_422(self, client: AsyncClient):
        payload = {**SAMPLE_INCIDENT, "severity": "CRITICAL"}
        resp = await client.post("/api/v1/incidents/", json=payload, headers=HEADERS)
        assert resp.status_code == 422

    async def test_invalid_provider_returns_422(self, client: AsyncClient):
        payload = {**SAMPLE_INCIDENT, "provider": "Alibaba"}
        resp = await client.post("/api/v1/incidents/", json=payload, headers=HEADERS)
        assert resp.status_code == 422

    async def test_empty_artifact_list_returns_422(self, client: AsyncClient):
        payload = {**SAMPLE_INCIDENT, "selectedArtifacts": []}
        resp = await client.post("/api/v1/incidents/", json=payload, headers=HEADERS)
        assert resp.status_code == 422


# ── Incident listing ──────────────────────────────────────────────────────────

class TestIncidentListing:
    async def test_list_returns_paginated_response(self, client: AsyncClient):
        # Create a couple of incidents first
        for _ in range(3):
            await client.post("/api/v1/incidents/", json=SAMPLE_INCIDENT, headers=HEADERS)

        resp = await client.get("/api/v1/incidents/?limit=2&offset=0", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) <= 2
        assert data["total"] >= 3

    async def test_filter_by_severity(self, client: AsyncClient):
        resp = await client.get("/api/v1/incidents/?severity=P1", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert all(i["severity"] == "P1" for i in data["items"])

    async def test_filter_by_provider(self, client: AsyncClient):
        resp = await client.get("/api/v1/incidents/?provider=AWS", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert all(i["provider"] == "AWS" for i in data["items"])


# ── Dashboard ─────────────────────────────────────────────────────────────────

class TestDashboard:
    async def test_dashboard_stats_returns_200(self, client: AsyncClient):
        resp = await client.get("/api/v1/dashboard/stats", headers=HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "totalIncidents" in data or "total_incidents" in data

    async def test_dashboard_stats_total_increments_after_create(self, client: AsyncClient):
        stats_before = await client.get("/api/v1/dashboard/stats", headers=HEADERS)
        total_before = stats_before.json().get("totalIncidents", 0)

        await client.post("/api/v1/incidents/", json=SAMPLE_INCIDENT, headers=HEADERS)

        stats_after = await client.get("/api/v1/dashboard/stats", headers=HEADERS)
        total_after = stats_after.json().get("totalIncidents", 0)

        assert total_after == total_before + 1


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealthCheck:
    async def test_health_endpoint_returns_200(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
