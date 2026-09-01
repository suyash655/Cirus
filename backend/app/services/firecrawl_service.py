"""CIRUS — Service: Firecrawl web-scraping / enrichment.

When FIRECRAWL_ENABLED=true and FIRECRAWL_API_KEY is set, calls the real
Firecrawl REST API to scrape and extract content from URLs.

Falls back to a lightweight stub when disabled or no key is provided.

Also exports the helper `get_context(provider, root_cause)` used by the
legacy run_workflow orchestrator.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

_FIRECRAWL_SCRAPE_URL = f"{settings.FIRECRAWL_BASE_URL}/scrape"
_FIRECRAWL_SEARCH_URL = f"{settings.FIRECRAWL_BASE_URL}/search"


class FirecrawlService:
    """Scrape / enrich a list of URLs via the Firecrawl API.

    If Firecrawl is disabled or the key is missing the service silently
    returns empty results so the pipeline can continue.
    """

    def __init__(self) -> None:
        self._enabled = settings.FIRECRAWL_ENABLED and bool(settings.FIRECRAWL_API_KEY)
        self._headers = {
            "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
            "Content-Type": "application/json",
        }
        if self._enabled:
            log.info("FirecrawlService initialised (live mode)")
        else:
            log.info("FirecrawlService initialised (stub mode — disabled or no key)")

    async def enrich_from_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape a list of URLs and return extracted markdown content."""
        if not self._enabled or not urls:
            return [{"url": url, "content": ""} for url in urls]

        results: List[Dict[str, Any]] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for url in urls:
                try:
                    resp = await client.post(
                        _FIRECRAWL_SCRAPE_URL,
                        headers=self._headers,
                        json={
                            "url": url,
                            "formats": ["markdown"],
                            "onlyMainContent": True,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = (
                        data.get("data", {}).get("markdown")
                        or data.get("markdown")
                        or ""
                    )
                    results.append({"url": url, "content": content})
                    log.debug("firecrawl scraped url", extra={"url": url, "chars": len(content)})
                except Exception as exc:
                    log.warning("firecrawl failed for url", extra={"url": url, "error": str(exc)})
                    results.append({"url": url, "content": "", "error": str(exc)})

        return results

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Run a Firecrawl search and return snippets."""
        if not self._enabled:
            return []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    _FIRECRAWL_SEARCH_URL,
                    headers=self._headers,
                    json={"query": query, "limit": limit},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", [])
        except Exception as exc:
            log.warning("firecrawl search failed", extra={"query": query, "error": str(exc)})
            return []


# ── Legacy helper used by run_workflow in orchestrator.py ─────────────────────

async def get_context(provider: str, root_cause: str) -> List[Dict[str, Any]]:
    """Search for relevant context about a cloud provider incident."""
    svc = FirecrawlService()
    query = f"{provider} cloud incident {root_cause} remediation runbook"
    results = await svc.search(query, limit=5)

    citations = []
    for item in results:
        citations.append(
            {
                "url": item.get("url", ""),
                "snippet": item.get("markdown") or item.get("description") or "",
                "title": item.get("title", ""),
            }
        )
    return citations
