"""CIRUS — Unique ID generation utilities."""
from __future__ import annotations

import uuid


def new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def incident_id() -> str:
    return f"inc-{uuid.uuid4().hex[:12]}"


def run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def artifact_id() -> str:
    return f"art-{uuid.uuid4().hex[:12]}"


def citation_id() -> str:
    return f"cit-{uuid.uuid4().hex[:12]}"


def knowledge_id() -> str:
    return f"kn-{uuid.uuid4().hex[:12]}"
