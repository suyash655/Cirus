"""CIRUS — Orchestrator: Temporal Client."""
import logging
from temporalio.client import Client

log = logging.getLogger(__name__)

_temporal_client = None

async def get_temporal_client() -> Client:
    """Get or initialize the Temporal client."""
    global _temporal_client
    if _temporal_client is None:
        log.info("Connecting to Temporal server at localhost:7233")
        try:
            _temporal_client = await Client.connect("localhost:7233")
        except Exception as e:
            log.warning(f"Could not connect to Temporal Server: {e}")
            raise
    return _temporal_client
