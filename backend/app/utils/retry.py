"""CIRUS — Async retry utilities with exponential backoff."""
from __future__ import annotations

import asyncio
import functools
import random
from typing import Any, Callable, Tuple, Type

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


async def retry_async(
    func: Callable,
    *args: Any,
    retries: int | None = None,
    backoff_base: float | None = None,
    backoff_max: float | None = None,
    jitter: bool = True,
    reraise_on: Tuple[Type[Exception], ...] = (),
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
            return await func(*args, **kwargs)
        except reraise_on as exc:
            raise exc
        except Exception as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                break
            wait = min(base ** attempt, cap)
            if jitter:
                wait *= 0.5 + random.random() * 0.5
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
    reraise_on: Tuple[Type[Exception], ...] = (),
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
                reraise_on=reraise_on,
                **kwargs,
            )
        return wrapper
    return decorator
