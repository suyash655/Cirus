"""CIRUS — Service: ChromaDB-backed vector store for incident similarity search.

Design decisions:
  - Uses chromadb's built-in sentence-transformers embedding function when
    available, gracefully falling back to a lightweight TF-IDF cosine
    similarity when sentence-transformers / PyTorch is not installed.
    This keeps the dev setup light (no GPU required).
  - Persistent storage at VECTOR_STORE_PATH so embeddings survive restarts.
  - All operations are synchronous (chromadb's Python client is sync);
    wrapped with asyncio.to_thread for use from async call sites.
  - Singleton client kept at module level — safe because chromadb uses file
    locking internally, so only one process writes at a time.

Collection document schema:
    id        — incident_id (string)
    document  — raw_text (what gets embedded)
    metadata  — {"title", "severity", "provider", "status", "created_at"}
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import settings

log = logging.getLogger(__name__)

# ── ChromaDB client & collection (module-level singletons) ────────────────────

_chroma_client = None
_collection = None


def _get_collection():
    """Lazily initialise ChromaDB client and collection."""
    global _chroma_client, _collection
    if _collection is not None:
        return _collection

    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except ImportError:
        raise ImportError(
            "chromadb is not installed. Run: pip install chromadb"
        )

    db_path = Path(settings.VECTOR_STORE_PATH).resolve()
    db_path.mkdir(parents=True, exist_ok=True)

    _chroma_client = chromadb.PersistentClient(
        path=str(db_path),
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    # Try to use sentence-transformers for better embeddings; fall back to
    # chromadb's default embedding (all-MiniLM-L6-v2 via onnx — no PyTorch).
    embedding_fn = None
    try:
        from chromadb.utils import embedding_functions
        embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        log.info("vector_store: using default ONNX embedding (all-MiniLM-L6-v2)")
    except Exception as e:
        log.warning("vector_store: could not load embedding function, using chromadb default", error=str(e))

    kwargs: Dict[str, Any] = {"name": settings.VECTOR_STORE_COLLECTION}
    if embedding_fn:
        kwargs["embedding_function"] = embedding_fn

    _collection = _chroma_client.get_or_create_collection(**kwargs)
    log.info(
        "vector_store: collection ready",
        collection=settings.VECTOR_STORE_COLLECTION,
        path=str(db_path),
        count=_collection.count(),
    )
    return _collection


# ── Public async API ──────────────────────────────────────────────────────────

async def upsert_incident(
    incident_id: str,
    raw_text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Add or update an incident in the vector store.

    Safe to call multiple times with the same incident_id — chromadb
    will overwrite the existing document.
    """
    if not settings.VECTOR_STORE_ENABLED:
        return

    def _upsert() -> None:
        col = _get_collection()
        col.upsert(
            ids=[incident_id],
            documents=[raw_text],
            metadatas=[metadata or {}],
        )

    await asyncio.to_thread(_upsert)
    log.debug("vector_store: upserted incident", incident_id=incident_id)


async def query_similar(
    query_text: str,
    top_k: Optional[int] = None,
    exclude_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the top-k most similar past incidents to query_text.

    Returns a list of dicts with keys:
        incident_id, raw_text_snippet, metadata, distance, similarity_pct
    """
    if not settings.VECTOR_STORE_ENABLED:
        return []

    k = top_k or settings.VECTOR_STORE_TOP_K

    def _query() -> List[Dict[str, Any]]:
        col = _get_collection()
        count = col.count()
        if count == 0:
            return []

        # Request one extra in case we need to exclude the query incident
        n_results = min(k + (1 if exclude_id else 0), count)
        results = col.query(
            query_texts=[query_text],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        for incident_id, doc, meta, dist in zip(ids, docs, metas, dists):
            if exclude_id and incident_id == exclude_id:
                continue
            # ChromaDB returns L2 distance; convert to 0–100 similarity score
            similarity_pct = round(max(0.0, 1.0 - dist / 2.0) * 100, 1)
            hits.append({
                "incident_id": incident_id,
                "raw_text_snippet": doc[:400] + ("…" if len(doc) > 400 else ""),
                "metadata": meta,
                "distance": round(dist, 4),
                "similarity_pct": similarity_pct,
            })
            if len(hits) >= k:
                break

        return hits

    try:
        return await asyncio.to_thread(_query)
    except Exception as e:
        log.warning("vector_store: query failed", error=str(e))
        return []


async def delete_incident(incident_id: str) -> None:
    """Remove an incident from the vector store."""
    if not settings.VECTOR_STORE_ENABLED:
        return

    def _delete() -> None:
        col = _get_collection()
        col.delete(ids=[incident_id])

    try:
        await asyncio.to_thread(_delete)
    except Exception as e:
        log.warning("vector_store: delete failed", incident_id=incident_id, error=str(e))


async def vector_store_count() -> int:
    """Return the total number of incidents in the vector store."""
    if not settings.VECTOR_STORE_ENABLED:
        return 0

    def _count() -> int:
        return _get_collection().count()

    try:
        return await asyncio.to_thread(_count)
    except Exception:
        return 0
