"""CIRUS — Service: LLM Router with MLflow-backed model registry.

WHY MLFLOW OVER W&B:
  1. Fully self-hostable — `mlflow server` needs no cloud account.
     W&B requires a cloud account, which breaks the "runs on fresh clone" constraint.
  2. MLflow's experiment/run model maps naturally to our evaluation workflow:
     each LLM call becomes a run within the "cirus-pipeline" experiment.
  3. The MLflow Model Registry lets us version prompt templates as artifacts,
     tag them as "Staging" or "Production", and gate promotion on eval metrics.
  4. For an interview: "We use MLflow because it's the open standard.
     Swapping to W&B is a one-line tracking_uri change."

ROUTING LOGIC:
  - 100% of traffic goes to the "control" model (current production prompt+model).
  - When a candidate is configured (CANDIDATE_MODEL, CANDIDATE_PROMPT_VERSION,
    CANDIDATE_TRAFFIC_PCT), that percentage of calls are routed to the candidate.
  - Candidate eval scores are compared against control in MLflow.
  - Promotion requires candidate to beat control on faithfulness AND syntax validity.
  - A candidate that is cheaper/faster but less faithful is BLOCKED from promotion.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm_service import LLMMessage, LLMResponse, LLMService

log = logging.getLogger(__name__)


# ── MLflow integration ────────────────────────────────────────────────────────

def _get_mlflow_client():
    """Get MLflow tracking client. Returns None if MLflow not configured."""
    try:
        import mlflow
        tracking_uri = getattr(settings, "MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(tracking_uri)
        return mlflow
    except ImportError:
        log.warning("MLflow not installed — prompt versioning disabled")
        return None


def log_llm_call_to_mlflow(
    mlflow,
    stage: str,
    model_id: str,
    prompt_version: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    faithfulness_score: Optional[float] = None,
    syntax_valid: Optional[bool] = None,
    is_candidate: bool = False,
) -> None:
    """Log a single LLM call as an MLflow run for eval comparison."""
    try:
        experiment_name = "cirus-pipeline-candidate" if is_candidate else "cirus-pipeline-control"
        mlflow.set_experiment(experiment_name)
        with mlflow.start_run(run_name=f"{stage}-{model_id[:20]}"):
            mlflow.log_param("stage", stage)
            mlflow.log_param("model_id", model_id)
            mlflow.log_param("prompt_version", prompt_version)
            mlflow.log_param("is_candidate", is_candidate)
            mlflow.log_metric("tokens_in", tokens_in)
            mlflow.log_metric("tokens_out", tokens_out)
            mlflow.log_metric("latency_ms", latency_ms)
            if faithfulness_score is not None:
                mlflow.log_metric("faithfulness", faithfulness_score)
            if syntax_valid is not None:
                mlflow.log_metric("syntax_valid", 1.0 if syntax_valid else 0.0)
    except Exception as e:
        log.warning(f"MLflow logging failed (non-fatal): {e}")


# ── Routing decision ──────────────────────────────────────────────────────────

def _should_use_candidate(incident_id: str, candidate_traffic_pct: float) -> bool:
    """
    Deterministically route a request to candidate or control using incident_id hash.
    Same incident always goes to same variant (for reproducibility).
    candidate_traffic_pct: 0.0 to 1.0
    """
    if candidate_traffic_pct <= 0.0:
        return False
    if candidate_traffic_pct >= 1.0:
        return True
    # Use last 2 bytes of SHA256 as a 0-65535 int for bucketing
    h = int(hashlib.sha256(incident_id.encode()).hexdigest()[-4:], 16)
    return h < int(candidate_traffic_pct * 65536)


# ── LLM Router ────────────────────────────────────────────────────────────────

class LLMRouter:
    """
    Routes LLM calls between a control model and a candidate model.

    The candidate is only promoted to 100% traffic if:
      - Its mean faithfulness score > control's mean faithfulness
      - Its syntax validity rate >= control's syntax validity rate
      - It has at least MIN_CANDIDATE_CALLS calls before comparison

    A candidate that is cheaper or faster but less faithful is BLOCKED.
    """

    MIN_CANDIDATE_CALLS = 10  # Minimum calls before comparing scores

    def __init__(
        self,
        incident_id: str,
        stage: str = "unknown",
        prompt_version: str = "v1",
    ):
        self._incident_id = incident_id
        self._stage = stage
        self._prompt_version = prompt_version

        # Control: production model
        self._control_llm = LLMService()

        # Candidate: configured via env vars
        candidate_pct = float(getattr(settings, "CANDIDATE_TRAFFIC_PCT", 0.0))
        self._use_candidate = _should_use_candidate(incident_id, candidate_pct)
        self._candidate_llm: Optional[LLMService] = None

        if self._use_candidate:
            self._candidate_llm = self._init_candidate()

        self._mlflow = _get_mlflow_client()

    def _init_candidate(self) -> Optional[LLMService]:
        """Initialize candidate LLM from CANDIDATE_MODEL env var."""
        candidate_model = getattr(settings, "CANDIDATE_MODEL", "")
        if not candidate_model:
            return None

        try:
            # Override the model for candidate
            import copy
            candidate = LLMService()
            candidate._model = candidate_model
            log.info(f"LLMRouter: routing to candidate model {candidate_model}")
            return candidate
        except Exception as e:
            log.warning(f"Failed to initialize candidate LLM: {e}")
            return None

    async def complete(
        self,
        messages: List[LLMMessage],
        system: str = "",
    ) -> LLMResponse:
        """Route the completion to control or candidate and log to MLflow."""
        llm = self._candidate_llm if (self._use_candidate and self._candidate_llm) else self._control_llm
        is_candidate = self._use_candidate and self._candidate_llm is not None

        start = time.perf_counter()
        response = await llm.complete(messages=messages, system=system)
        latency_ms = (time.perf_counter() - start) * 1000

        if self._mlflow:
            log_llm_call_to_mlflow(
                self._mlflow,
                stage=self._stage,
                model_id=response.model_id or llm._model,
                prompt_version=self._prompt_version,
                tokens_in=sum(len(m.content.split()) for m in messages),
                tokens_out=response.tokens_used,
                latency_ms=latency_ms,
                is_candidate=is_candidate,
            )

        return response


# ── Promotion comparison ──────────────────────────────────────────────────────

def compare_and_promote_candidate() -> Dict[str, Any]:
    """
    Compare control vs candidate eval scores and determine if candidate should be promoted.

    Returns a dict with:
      - recommendation: "promote" | "reject" | "insufficient_data"
      - reason: human-readable explanation
      - control_scores: {"faithfulness": float, "syntax_valid_rate": float}
      - candidate_scores: {"faithfulness": float, "syntax_valid_rate": float}

    PROMOTION RULES (order matters — first failing rule blocks promotion):
      1. Candidate must have >= MIN_CANDIDATE_CALLS runs.
      2. Candidate faithfulness >= control faithfulness (quality regression blocks).
      3. Candidate syntax validity >= control syntax validity (correctness regression blocks).
      4. If all gates pass → recommend promotion.

    Latency and cost are logged but do NOT block promotion.
    """
    mlflow = _get_mlflow_client()
    if not mlflow:
        return {"recommendation": "insufficient_data", "reason": "MLflow not configured"}

    try:
        from mlflow.tracking import MlflowClient
        client = MlflowClient()

        def _get_metric_mean(experiment_name: str, metric_key: str) -> Optional[float]:
            experiments = client.search_experiments(filter_string=f"name = '{experiment_name}'")
            if not experiments:
                return None
            runs = client.search_runs(
                experiment_ids=[e.experiment_id for e in experiments],
                max_results=100,
                order_by=["start_time DESC"],
            )
            values = [r.data.metrics.get(metric_key) for r in runs if metric_key in r.data.metrics]
            return sum(values) / len(values) if values else None

        control_faith = _get_metric_mean("cirus-pipeline-control", "faithfulness")
        candidate_faith = _get_metric_mean("cirus-pipeline-candidate", "faithfulness")
        control_syntax = _get_metric_mean("cirus-pipeline-control", "syntax_valid")
        candidate_syntax = _get_metric_mean("cirus-pipeline-candidate", "syntax_valid")

        # Count candidate runs
        cand_experiments = client.search_experiments(filter_string="name = 'cirus-pipeline-candidate'")
        cand_run_count = 0
        if cand_experiments:
            runs = client.search_runs([e.experiment_id for e in cand_experiments])
            cand_run_count = len(runs)

        if cand_run_count < LLMRouter.MIN_CANDIDATE_CALLS:
            return {
                "recommendation": "insufficient_data",
                "reason": f"Candidate has only {cand_run_count} runs; need {LLMRouter.MIN_CANDIDATE_CALLS}",
            }

        if candidate_faith is None or control_faith is None:
            return {"recommendation": "insufficient_data", "reason": "Faithfulness scores not yet recorded"}

        # Gate 1: Faithfulness must not regress
        if candidate_faith < control_faith:
            return {
                "recommendation": "reject",
                "reason": (
                    f"Candidate faithfulness ({candidate_faith:.3f}) < "
                    f"control faithfulness ({control_faith:.3f}). "
                    "Quality regression blocks promotion regardless of cost/speed."
                ),
                "control_scores": {"faithfulness": control_faith, "syntax_valid_rate": control_syntax},
                "candidate_scores": {"faithfulness": candidate_faith, "syntax_valid_rate": candidate_syntax},
            }

        # Gate 2: Syntax validity must not regress
        if candidate_syntax is not None and control_syntax is not None:
            if candidate_syntax < control_syntax:
                return {
                    "recommendation": "reject",
                    "reason": (
                        f"Candidate syntax validity ({candidate_syntax:.3f}) < "
                        f"control ({control_syntax:.3f}). "
                        "Correctness regression blocks promotion."
                    ),
                    "control_scores": {"faithfulness": control_faith, "syntax_valid_rate": control_syntax},
                    "candidate_scores": {"faithfulness": candidate_faith, "syntax_valid_rate": candidate_syntax},
                }

        return {
            "recommendation": "promote",
            "reason": f"Candidate passed all quality gates (faith={candidate_faith:.3f}, syntax={candidate_syntax:.3f})",
            "control_scores": {"faithfulness": control_faith, "syntax_valid_rate": control_syntax},
            "candidate_scores": {"faithfulness": candidate_faith, "syntax_valid_rate": candidate_syntax},
        }

    except Exception as e:
        return {"recommendation": "insufficient_data", "reason": f"MLflow query error: {e}"}
