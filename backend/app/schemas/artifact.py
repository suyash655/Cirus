"""CIRUS — Pydantic v2 schemas: all Artifact types."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

# ── Shared ────────────────────────────────────────────────────────────────────

ArtifactType = Literal["rca", "policy", "iac", "alerts", "runbook", "regression"]


class ActionItemRead(BaseModel):
    id: str
    title: str
    priority: Literal["high", "medium", "low"]
    owner: str
    due_date: str
    status: Literal["open", "in-progress", "done"]


# ── RCA ───────────────────────────────────────────────────────────────────────

class ImpactAnalysis(BaseModel):
    affected_systems: List[str]
    user_impact: str
    data_scoping_note: str
    estimated_duration: str


class RCAArtifact(BaseModel):
    type: Literal["rca"] = "rca"
    executive_summary: str
    root_cause: str
    contributing_factors: List[str]
    impact_analysis: ImpactAnalysis
    lessons_learned: List[str]
    action_items: List[ActionItemRead]


# ── Policy ────────────────────────────────────────────────────────────────────

class PolicyArtifact(BaseModel):
    type: Literal["policy"] = "policy"
    language: Literal["rego", "scp", "sentinel"]
    description: str
    code: str
    tests: str
    rationale: str
    enforcement: Literal["deny", "warn", "audit"]


# ── IaC ───────────────────────────────────────────────────────────────────────

class IaCArtifact(BaseModel):
    type: Literal["iac"] = "iac"
    tool: Literal["terraform", "cdk", "pulumi", "cloudformation"]
    description: str
    diff: str
    full_patch: str
    affected_resources: List[str]
    breaking_change: bool


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertRule(BaseModel):
    name: str
    severity: Literal["critical", "warning", "info"]
    expression: str
    duration: str
    labels: Dict[str, str] = {}
    annotations: Dict[str, str] = {}


class AlertsArtifact(BaseModel):
    type: Literal["alerts"] = "alerts"
    provider: Literal["prometheus", "cloudwatch", "datadog", "generic"]
    description: str
    rules: List[AlertRule]


# ── Runbook ───────────────────────────────────────────────────────────────────

class RunbookStep(BaseModel):
    id: int
    title: str
    description: str
    command: Optional[str] = None
    note: Optional[str] = None
    severity_gate: Optional[str] = None
    expected_output: Optional[str] = None


class RunbookArtifact(BaseModel):
    type: Literal["runbook"] = "runbook"
    title: str
    description: str
    prerequisites: List[str]
    steps: List[RunbookStep]
    escalation: str
    references: List[str]


# ── Regression ────────────────────────────────────────────────────────────────

class TestCase(BaseModel):
    id: str
    name: str
    description: str
    category: Literal["positive", "negative", "boundary"]
    code: str
    expected_result: str


class RegressionArtifact(BaseModel):
    type: Literal["regression"] = "regression"
    framework: Literal["pytest", "jest", "go-test", "junit"]
    description: str
    test_cases: List[TestCase]


# ── Union ─────────────────────────────────────────────────────────────────────

AnyArtifact = Union[
    RCAArtifact,
    PolicyArtifact,
    IaCArtifact,
    AlertsArtifact,
    RunbookArtifact,
    RegressionArtifact,
]


class ArtifactRead(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    incident_id: str
    artifact_type: ArtifactType
    content: Dict[str, Any]   # free-form; LLM output may vary
    version: int
    model_id: Optional[str] = None
    tokens_used: Optional[int] = None


class ArtifactSetRead(BaseModel):
    rca: Optional[ArtifactRead] = None
    policy: Optional[ArtifactRead] = None
    iac: Optional[ArtifactRead] = None
    alerts: Optional[ArtifactRead] = None
    runbook: Optional[ArtifactRead] = None
    regression: Optional[ArtifactRead] = None


class RegenerateArtifactRequest(BaseModel):
    artifact_type: ArtifactType
    hint: Optional[str] = Field(None, description="Optional user hint for regeneration.")
