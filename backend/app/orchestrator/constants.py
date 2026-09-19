"""CIRUS — Orchestrator: Stage ID constants.

All pipeline stage identifiers are defined here as a single source of truth.
Import from this module instead of using raw strings anywhere in the codebase.
"""
from __future__ import annotations


class StageID:
    """Pipeline stage identifier constants."""
    NORMALIZATION = "normalization"
    ROOT_CAUSE = "root-cause-classification"
    CONTEXT_ENRICHMENT = "context-enrichment"
    ARTIFACT_GENERATION = "artifact-generation"
    VALIDATOR_CRITIC = "validator-critic"
    RISK_SCORING = "risk-scoring"
    CITATION_EXTRACTION = "citation-extraction"

    ALL: tuple[str, ...] = (
        NORMALIZATION,
        ROOT_CAUSE,
        CONTEXT_ENRICHMENT,
        ARTIFACT_GENERATION,
        VALIDATOR_CRITIC,
        RISK_SCORING,
        CITATION_EXTRACTION,
    )
