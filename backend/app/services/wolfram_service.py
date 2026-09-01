"""CIRUS — Service: Wolfram Alpha risk scoring.

When WOLFRAM_ENABLED=true and WOLFRAM_APP_ID is set, calls the real
Wolfram Alpha Short-Answers API to compute a numeric risk score for a
given severity string.

Falls back to a heuristic calculation when disabled / no key available
so the pipeline never hard-fails because of a missing Wolfram credential.

Also exports the helper `calculate_risk(severity)` used by the legacy
run_workflow orchestrator.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

# Severity → baseline risk score (0-100)
_SEVERITY_SCORES: Dict[str, int] = {
    "critical": 90,
    "p1": 90,
    "high": 70,
    "p2": 70,
    "medium": 50,
    "p3": 50,
    "low": 25,
    "p4": 25,
}
_DEFAULT_SCORE = 50
# Assume remediation reduces risk by ~35 %
_REMEDIATION_DELTA = 35


class WolframService:
    """Risk scoring via Wolfram Alpha or local heuristics.

    The pipeline only calls `query()` for arbitrary maths queries.
    For the standard before/after risk pattern, use `score_risk()`.
    """

    def __init__(self) -> None:
        self._enabled = settings.WOLFRAM_ENABLED and bool(settings.WOLFRAM_APP_ID)
        if self._enabled:
            log.info("WolframService initialised (live mode)")
        else:
            log.info("WolframService initialised (heuristic mode — disabled or no APP_ID)")

    async def query(self, query_str: str) -> Dict[str, Any]:
        """Run a short-answers query against Wolfram Alpha."""
        if not self._enabled:
            return {"result": self._heuristic_answer(query_str), "source": "heuristic"}

        params = {
            "appid": settings.WOLFRAM_APP_ID,
            "i": query_str,
            "output": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(settings.WOLFRAM_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                # Extract the primary result pod value
                for pod in data.get("queryresult", {}).get("pods", []):
                    if pod.get("primary") or pod.get("id") == "Result":
                        subpods = pod.get("subpods", [])
                        if subpods:
                            return {
                                "result": subpods[0].get("plaintext", ""),
                                "source": "wolfram",
                            }
                return {"result": str(data), "source": "wolfram"}
        except Exception as exc:
            log.warning("wolfram query failed, falling back to heuristic", extra={"error": str(exc)})
            return {"result": self._heuristic_answer(query_str), "source": "heuristic"}

    async def score_risk(self, severity: str) -> Tuple[int, int]:
        """Return (risk_before, risk_after) for a given severity string."""
        severity_key = severity.lower().strip()
        base = _SEVERITY_SCORES.get(severity_key, _DEFAULT_SCORE)

        if self._enabled:
            # Ask Wolfram to compute the post-remediation score
            query_str = (
                f"Given a cloud incident risk score of {base} out of 100, "
                f"what is the score after applying a 35 percent risk reduction?"
            )
            result = await self.query(query_str)
            raw = result.get("result", "")
            try:
                # Wolfram may return "42.25" or "42" etc.
                after = int(float("".join(c for c in raw if c.isdigit() or c == ".")))
                after = max(0, min(100, after))
            except (ValueError, TypeError):
                after = max(0, base - _REMEDIATION_DELTA)
        else:
            after = max(0, base - _REMEDIATION_DELTA)

        log.debug(
            "risk scored",
            extra={"severity": severity, "before": base, "after": after},
        )
        return base, after

    # ── Private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _heuristic_answer(query_str: str) -> str:
        """Very simple numeric extraction fallback."""
        import re
        numbers = re.findall(r"\d+\.?\d*", query_str)
        if numbers:
            val = float(numbers[-1])
            reduced = round(val * (1 - _REMEDIATION_DELTA / 100), 2)
            return str(reduced)
        return str(_DEFAULT_SCORE - _REMEDIATION_DELTA)


# ── Legacy helper used by run_workflow in orchestrator.py ─────────────────────

async def calculate_risk(severity: str) -> Tuple[int, int]:
    """Return (risk_before, risk_after) for a severity string."""
    svc = WolframService()
    return await svc.score_risk(severity)
