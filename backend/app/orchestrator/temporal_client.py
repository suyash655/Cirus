"""CIRUS — Orchestrator: Temporal Client (settings-driven)."""
import logging
from typing import Optional

from temporalio.client import Client

from app.core.config import settings

log = logging.getLogger(__name__)

_temporal_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """Get or lazily initialise the Temporal client.

    Uses TEMPORAL_HOST and TEMPORAL_NAMESPACE from settings so it can be
    pointed at a local dev server, Temporal Cloud, or a Docker service
    without code changes.
    """
    global _temporal_client
    if _temporal_client is None:
        host = settings.TEMPORAL_HOST
        namespace = settings.TEMPORAL_NAMESPACE
        log.info("Connecting to Temporal server", host=host, namespace=namespace)
        try:
            _temporal_client = await Client.connect(host, namespace=namespace)
            log.info("Temporal client connected", host=host)
        except Exception as e:
            log.warning("Could not connect to Temporal Server", host=host, error=str(e))
            raise
    return _temporal_client


def reset_temporal_client() -> None:
    """Force the next call to get_temporal_client() to create a new connection.

    Useful in tests or after a Temporal server restart.
    """
    global _temporal_client
    _temporal_client = None
