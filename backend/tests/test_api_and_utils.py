"""CIRUS — Unit tests for API utilities, domain errors, retry engine, and GitOps service."""
import pytest
import asyncio
from app.utils.retry import retry_async, is_transient_error
from app.core.errors import (
    NotFoundError,
    ValidationError,
    RateLimitError,
    AuthenticationError,
    AuthorizationError,
    ServiceUnavailableError,
)
from app.services.gitops_service import GitOpsService, CreatePRRequest


@pytest.mark.asyncio
async def test_retry_async_success():
    call_count = 0

    async def successful_func():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await retry_async(successful_func, retries=2, backoff_base=0.01)
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_async_eventual_success():
    call_count = 0

    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary glitch")
        return "recovered"

    result = await retry_async(flaky_func, retries=3, backoff_base=0.01, jitter=False)
    assert result == "recovered"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_async_timeout_per_attempt():
    async def slow_func():
        await asyncio.sleep(0.5)
        return "too late"

    with pytest.raises(asyncio.TimeoutError):
        await retry_async(slow_func, retries=1, backoff_base=0.01, attempt_timeout=0.05)


def test_is_transient_error():
    assert is_transient_error(ConnectionError("socket lost")) is True
    assert is_transient_error(TimeoutError("timed out")) is True
    assert is_transient_error(ValueError("invalid format")) is False

    class MockHTTPError(Exception):
        status_code = 503

    assert is_transient_error(MockHTTPError("service unavailable")) is True

    class Mock429Error(Exception):
        status_code = 429

    assert is_transient_error(Mock429Error("rate limited")) is True


def test_domain_exceptions():
    nf = NotFoundError("Incident", "inc-123")
    assert nf.status_code == 404
    assert nf.code == "NOT_FOUND"
    assert "inc-123" in nf.message

    rl = RateLimitError(retry_after=45)
    assert rl.status_code == 429
    assert rl.code == "RATE_LIMIT_EXCEEDED"
    assert rl.retry_after == 45

    auth = AuthenticationError()
    assert auth.status_code == 401

    su = ServiceUnavailableError(service="Temporal")
    assert su.status_code == 503
    assert su.detail["service"] == "Temporal"


def test_gitops_service_create_pr():
    req = CreatePRRequest(
        incident_id="inc-test-99",
        target_repo="suyash655/cirus",
        artifacts=["policy", "iac", "alerts"],
    )
    res = GitOpsService.create_remediation_pr(req)
    assert res.success is True
    assert "suyash655/cirus/pull/" in res.pr_url
    assert "cirus/remediation-" in res.branch_name
    assert len(res.files_committed) == 3
    assert res.commit_sha
    assert res.diff_preview is not None
