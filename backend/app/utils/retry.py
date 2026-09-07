"""CIRUS — Async retry utilities with exponential backoff and jitter."""
from __future__ import annotations

import asyncio
import functools
import random
import time
from typing import Any, Callable, Tuple, Type

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)

TRANSIENT_STATUS_CODES = {429, 502, 503, 504}


def is_transient_error(exc: Exception) -> bool:
    """Detect transient network timeouts, connection failures, and 429/5xx status codes."""
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int) and status in TRANSIENT_STATUS_CODES:
        return True
    response = getattr(exc, "response", None)
    if response and hasattr(response, "status_code"):
        if response.status_code in TRANSIENT_STATUS_CODES:
            return True
    return False


async def retry_async(
    func: Callable,
    *args: Any,
    retries: int | None = None,
    backoff_base: float | None = None,
    backoff_max: float | None = None,
    jitter: bool = True,
    reraise_on: Tuple[Type[Exception], ...] = (),
    retry_if: Callable[[Exception], bool] | None = None,
    attempt_timeout: float | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an async callable with exponential backoff retries.

    Args:
        func: The async function to call.
        *args: Positional arguments for func.
        retries: Number of retry attempts (default: settings.MAX_RETRIES).
        backoff_base: Base backoff multiplier in seconds.
        backoff_max: Maximum backoff in seconds.
        jitter: Whether to add random jitter to backoff.
        reraise_on: Exception types to re-raise immediately without retrying.
        retry_if: Optional predicate returning True if an exception should be retried.
        attempt_timeout: Max seconds to allow per attempt.
        **kwargs: Keyword arguments for func.

    Returns:
        The result of func on success.

    Raises:
        The last exception raised after all retries are exhausted.
    """
    max_attempts = (retries or settings.MAX_RETRIES) + 1
    base = backoff_base or settings.RETRY_BACKOFF_BASE
    cap = backoff_max or settings.RETRY_BACKOFF_MAX

    last_exc: Exception | None = None

    for attempt in range(max_attempts):
        try:
            if attempt_timeout is not None and attempt_timeout > 0:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=attempt_timeout)
            return await func(*args, **kwargs)
        except reraise_on as exc:
            raise exc
        except Exception as exc:
            last_exc = exc
            if retry_if is not None and not retry_if(exc):
                raise exc

            if attempt == max_attempts - 1:
                break

            # Exponential backoff with full jitter: wait in [0, min(cap, base * 2^attempt)]
            raw_backoff = min(base * (2 ** attempt), cap)
            wait = random.uniform(0.1, raw_backoff) if jitter else raw_backoff

            log.warning(
                "retry scheduled",
                func=getattr(func, "__name__", str(func)),
                attempt=attempt + 1,
                max_attempts=max_attempts,
                wait_s=round(wait, 2),
                error=str(exc),
            )
            await asyncio.sleep(wait)

    raise last_exc  # type: ignore[misc]


def with_retry(
    retries: int | None = None,
    backoff_base: float | None = None,
    backoff_max: float | None = None,
    jitter: bool = True,
    reraise_on: Tuple[Type[Exception], ...] = (),
    retry_if: Callable[[Exception], bool] | None = None,
    attempt_timeout: float | None = None,
):
    """Decorator that adds retry logic to an async function."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await retry_async(
                func,
                *args,
                retries=retries,
                backoff_base=backoff_base,
                backoff_max=backoff_max,
                jitter=jitter,
                reraise_on=reraise_on,
                retry_if=retry_if,
                attempt_timeout=attempt_timeout,
                **kwargs,
            )
        return wrapper
    return decorator

