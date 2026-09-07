import { delay } from './utils';
import {
  MOCK_INCIDENTS,
  MOCK_INCIDENT_DETAILS,
  MOCK_ARTIFACT_SETS,
  MOCK_WORKFLOW_RUNS,
  MOCK_RISK_SCORES,
  MOCK_EXTRACTIONS,
  MOCK_DASHBOARD_STATS,
} from './mock-data';
import type {
  Incident,
  IncidentDetail,
  ArtifactSet,
  Artifact,
  ArtifactType,
  CreateIncidentPayload,
  CreateIncidentResponse,
  WorkflowRun,
  RiskScore,
  ExtractionResult,
  DashboardStats,
  CreatePRPayload,
  GitOpsPRResult,
  IncidentComplianceReport,
} from './types';
import { generateId } from './utils';


// ═══════════════════════════════════════════
// CIRUS — Typed Mock API Layer
// Replace each function body with real fetch() calls when backend is ready.
// All signatures and return types remain identical.
// ═══════════════════════════════════════════

class CirusAPIError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = 'CirusAPIError';
  }
}

// ─── In-memory store for created incidents (prototype mode) ──────────────────
const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === 'true';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'dev-api-key-12345';

function toSnake(value: string): string {
  return value.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

function toCamel(value: string): string {
  return value.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

function convertKeys(value: unknown, convert: (key: string) => string): unknown {
  if (Array.isArray(value)) return value.map((item) => convertKeys(item, convert));
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, child]) => [convert(key), convertKeys(child, convert)]),
  );
}

function snakeKeys<T>(value: unknown): T {
  return convertKeys(value, toSnake) as T;
}

function camelKeys<T>(value: unknown): T {
  return convertKeys(value, toCamel) as T;
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...init.headers,
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    let message = `Backend responded with ${response.status}`;
    try {
      const body = await response.json();
      if (Array.isArray(body.detail)) {
        message = body.detail
          .map((item: { loc?: Array<string | number>; msg?: string }) =>
            `${item.loc?.join('.') ?? 'request'}: ${item.msg ?? 'Invalid value'}`,
          )
          .join('; ');
      } else if (typeof body.detail === 'string') {
        message = body.detail;
      }
    } catch {
      // Keep the status-based message when the backend returns no JSON body.
    }
    throw new CirusAPIError('BACKEND_ERROR', message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

type BackendArtifact = {
  artifact_type: ArtifactType;
  content: unknown;
};

function mapArtifactSet(raw: Record<string, BackendArtifact | null | undefined>): ArtifactSet {
  const mapped: ArtifactSet = {};
  Object.entries(raw).forEach(([type, wrapper]) => {
    if (!wrapper?.content) return;
    (mapped as Record<string, unknown>)[type] = camelKeys(wrapper.content);
  });
  return mapped;
}

const incidentStore: Incident[] = [...MOCK_INCIDENTS];
const detailStore: Record<string, IncidentDetail> = { ...MOCK_INCIDENT_DETAILS };
const artifactStore: Record<string, ArtifactSet> = { ...MOCK_ARTIFACT_SETS };

// ─── API Implementation ───────────────────────────────────────────────────────

export async function getIncidents(): Promise<Incident[]> {
  if (!USE_MOCKS) {
    const data = await apiFetch<{ items: unknown[] }>('/incidents/?limit=100');
    return camelKeys<Incident[]>(data.items);
  }

  await delay(400 + Math.random() * 200);
  return [...incidentStore].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export async function getIncident(id: string): Promise<IncidentDetail> {
  if (!USE_MOCKS) {
    return camelKeys<IncidentDetail>(await apiFetch(`/incidents/${id}`));
  }

  await delay(300 + Math.random() * 150);
  const detail = detailStore[id];
  if (!detail) {
    throw new CirusAPIError('NOT_FOUND', `Incident '${id}' not found.`, 404);
  }
  return detail;
}

export async function getArtifacts(incidentId: string): Promise<ArtifactSet> {
  if (!USE_MOCKS) {
    return mapArtifactSet(await apiFetch<Record<string, BackendArtifact | null>>(`/artifacts/${incidentId}`));
  }

  await delay(500 + Math.random() * 300);
  const artifacts = artifactStore[incidentId];
  if (!artifacts) {
    return {};
  }
  return artifacts;
}

export async function regenerateArtifact(
  incidentId: string,
  type: ArtifactType,
): Promise<Artifact> {
  if (!USE_MOCKS) {
    const artifact = await apiFetch<BackendArtifact>(`/artifacts/${incidentId}/regenerate`, {
      method: 'POST',
      body: JSON.stringify({ artifact_type: type }),
    });
    return camelKeys<Artifact>(artifact.content);
  }

  await delay(1500 + Math.random() * 1000);
  const artifacts = artifactStore[incidentId];
  if (!artifacts) {
    throw new CirusAPIError('NOT_FOUND', `No artifacts for incident '${incidentId}'.`, 404);
  }
  const artifact = artifacts[type];
  if (!artifact) {
    throw new CirusAPIError(
      'ARTIFACT_NOT_FOUND',
      `Artifact '${type}' not found for incident '${incidentId}'.`,
      404,
    );
  }
  return artifact as Artifact;
}

export async function createIncident(
  payload: CreateIncidentPayload,
): Promise<CreateIncidentResponse> {
  if (!USE_MOCKS) {
    return camelKeys<CreateIncidentResponse>(
      await apiFetch('/incidents/', {
        method: 'POST',
        body: JSON.stringify(snakeKeys(payload)),
      }),
    );
  }

  await delay(800 + Math.random() * 400);

  const id = `inc-${generateId()}`;
  const now = new Date().toISOString();

  // Detect title from the first line of raw text
  const lines = payload.rawText.trim().split('\n');
  const title =
    lines[0].replace(/^#+\s*/, '').slice(0, 120) || 'Untitled Incident';

  const newIncident: Incident = {
    id,
    title,
    severity: payload.severity ?? 'P3',
    provider: payload.provider ?? 'Generic',
    status: 'processing',
    createdAt: now,
    updatedAt: now,
    summary: lines.slice(1, 4).join(' ').slice(0, 200) || 'Processing…',
    tags: [],
    artifactsReady: [],
  };

  const detail: IncidentDetail = {
    ...newIncident,
    rawText: payload.rawText,
    detectedFormat: 'plain',
    timeline: [],
  };

  incidentStore.unshift(newIncident);
  detailStore[id] = detail;

  // Simulate async processing — after 4s the incident becomes "ready"
  simulateProcessing(id, payload.selectedArtifacts);

  return { id, estimatedProcessingMs: 4000 };
}

// ─── Processing simulation ────────────────────────────────────────────────────
function simulateProcessing(id: string, selectedArtifacts: ArtifactType[]): void {
  const totalMs = 3500 + Math.random() * 1500;

  setTimeout(() => {
    const incident = incidentStore.find((i) => i.id === id);
    if (!incident) return;

    // Clone the full artifact set from inc-001 as template
    const baseArtifacts = MOCK_ARTIFACT_SETS['inc-001'];
    const filteredArtifacts: ArtifactSet = {};

    selectedArtifacts.forEach((type) => {
      if (baseArtifacts[type]) {
        (filteredArtifacts as Record<string, unknown>)[type] = baseArtifacts[type];
      }
    });

    artifactStore[id] = filteredArtifacts;

    incident.status = 'ready';
    incident.artifactsReady = selectedArtifacts;
    incident.updatedAt = new Date().toISOString();

    const detail = detailStore[id];
    if (detail) {
      detail.status = 'ready';
      detail.artifactsReady = selectedArtifacts;
      detail.updatedAt = incident.updatedAt;
    }
  }, totalMs);
}

export async function deleteIncident(id: string): Promise<void> {
  if (!USE_MOCKS) {
    await apiFetch<void>(`/incidents/${id}`, { method: 'DELETE' });
    return;
  }

  await delay(300);
  const idx = incidentStore.findIndex((i) => i.id === id);
  if (idx !== -1) {
    incidentStore.splice(idx, 1);
    delete detailStore[id];
    delete artifactStore[id];
  }
}

// ─── Workflow API ─────────────────────────────────────────────────────────────

const workflowStore: Record<string, WorkflowRun> = { ...MOCK_WORKFLOW_RUNS };

export async function getWorkflowRun(runId: string): Promise<WorkflowRun> {
  if (!USE_MOCKS) {
    return camelKeys<WorkflowRun>(await apiFetch(`/runs/${runId}`));
  }

  await delay(250 + Math.random() * 150);
  const run = workflowStore[runId];
  if (!run) throw new CirusAPIError('NOT_FOUND', `Workflow run '${runId}' not found.`, 404);
  return run;
}

export async function getWorkflowRunByIncident(incidentId: string): Promise<WorkflowRun | null> {
  if (!USE_MOCKS) {
    return camelKeys<WorkflowRun | null>(await apiFetch(`/runs/by-incident/${incidentId}`));
  }

  await delay(200);
  const run = Object.values(workflowStore).find((r) => r.incidentId === incidentId);
  return run ?? null;
}

// ─── Risk Score API ───────────────────────────────────────────────────────────

const riskStore: Record<string, RiskScore> = { ...MOCK_RISK_SCORES };

export async function getRiskScore(incidentId: string): Promise<RiskScore | null> {
  if (!USE_MOCKS) {
    const run = await getWorkflowRunByIncident(incidentId);
    const riskStage = run?.stages.find((stage) => stage.id === 'risk-scoring');
    const data = riskStage?.output?.data as Partial<RiskScore> | undefined;
    if (!data) return null;
    return {
      overall: Number(data.overall ?? 0),
      dimensions: data.dimensions ?? {
        exposure: { score: 0, label: 'Exposure', description: 'Unavailable' },
        blast_radius: { score: 0, label: 'Blast Radius', description: 'Unavailable' },
        recurrence: { score: 0, label: 'Recurrence Risk', description: 'Unavailable' },
        remediation_effort: { score: 0, label: 'Remediation Effort', description: 'Unavailable' },
      },
      beforeRemediation: Number(data.beforeRemediation ?? data.overall ?? 0),
      afterRemediation: Number(data.afterRemediation ?? 0),
      delta: Number(data.delta ?? 0),
      calculatedAt: run?.updatedAt ?? new Date().toISOString(),
    };
  }

  await delay(200 + Math.random() * 100);
  return riskStore[incidentId] ?? null;
}

// ─── Extraction API ───────────────────────────────────────────────────────────

const extractionStore: Record<string, ExtractionResult> = { ...MOCK_EXTRACTIONS };

export async function getExtraction(incidentId: string): Promise<ExtractionResult | null> {
  if (!USE_MOCKS) {
    const run = await getWorkflowRunByIncident(incidentId);
    const extractionStage = run?.stages.find((stage) => stage.id === 'normalization');
    const data = extractionStage?.output?.data as Partial<ExtractionResult> | undefined;
    if (!data) return null;
    return {
      title: String(data.title ?? ''),
      detectedProvider: data.detectedProvider ?? 'Generic',
      detectedSeverity: data.detectedSeverity ?? 'P3',
      affectedServices: data.affectedServices ?? [],
      timeRange: data.timeRange ?? { start: '', end: '' },
      errorMessages: data.errorMessages ?? [],
      structuredData: data.structuredData ?? {},
      confidence: Number(data.confidence ?? extractionStage?.confidence ?? 0),
      citations: data.citations ?? [],
    };
  }

  await delay(200 + Math.random() * 100);
  return extractionStore[incidentId] ?? null;
}


// ─── Dashboard Stats API ──────────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  if (!USE_MOCKS) {
    return camelKeys<DashboardStats>(await apiFetch('/dashboard/stats'));
  }

  await delay(300 + Math.random() * 150);

  // Dynamically compute from in-memory store so new incidents reflect
  const totalIncidents = incidentStore.length;
  const readyIncidents = incidentStore.filter((i) => i.status === 'ready');
  const guardrailsGenerated = readyIncidents.reduce(
    (acc, i) => acc + i.artifactsReady.length,
    0,
  );
  const riskScores = Object.values(riskStore);
  const avgRiskReduction =
    riskScores.length > 0
      ? Math.round(riskScores.reduce((s, r) => s + r.delta, 0) / riskScores.length)
      : 0;
  const awaitingApproval = readyIncidents.length;

  return {
    totalIncidents,
    guardrailsGenerated,
    avgRiskReduction,
    awaitingApproval,
    artifactSummary: MOCK_DASHBOARD_STATS.artifactSummary,
    riskTrend: MOCK_DASHBOARD_STATS.riskTrend,
    mttgHours: MOCK_DASHBOARD_STATS.mttgHours ?? 0,
  };
}

// ─── GitOps Pull Request API ──────────────────────────────────────────────────

export async function createGitOpsPR(payload: CreatePRPayload): Promise<GitOpsPRResult> {
  if (!USE_MOCKS) {
    const raw = await apiFetch<any>('/gitops/create-pr', {
      method: 'POST',
      body: JSON.stringify(snakeKeys(payload)),
    });
    return camelKeys<GitOpsPRResult>(raw);
  }

  await delay(600);
  const cleanId = payload.incidentId.replace('inc-', '').slice(0, 8);
  const repo = payload.targetRepo || 'suyash655/cirus';
  const prNum = 100 + (Math.abs(cleanId.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0)) % 800);
  return {
    success: true,
    prUrl: `https://github.com/${repo}/pull/${prNum}`,
    prNumber: prNum,
    branchName: `cirus/remediation-${cleanId}`,
    targetRepo: repo,
    filesCommitted: [
      `policies/guardrails/${cleanId}.rego`,
      `terraform/patches/${cleanId}_remediation.tf`,
      `docs/runbooks/${cleanId}_runbook.md`,
    ],
    commitSha: 'a7b3c9f2',
    diffPreview: '+# Automated remediation patch by CIRUS\n+resource "aws_s3_bucket_public_access_block" "enforce" {\n+  block_public_acls = true\n+}',
    message: `Successfully opened Pull Request #${prNum} on ${repo} from branch 'cirus/remediation-${cleanId}'. Automated CI regression and policy syntax checks triggered.`,
    createdAt: new Date().toISOString(),
  };
}

// ─── Compliance API ───────────────────────────────────────────────────────────

export async function getIncidentCompliance(incidentId: string): Promise<IncidentComplianceReport | null> {
  if (!USE_MOCKS) {
    return camelKeys<IncidentComplianceReport>(await apiFetch(`/compliance/${incidentId}`));
  }

  await delay(250);
  return {
    incident_id: incidentId,
    overall_compliance_score: 94,
    audit_readiness_status: 'AUDIT_READY',
    verified_claims_count: 5,
    soc2_controls: [
      {
        id: 'CC6.1',
        framework: 'SOC2_TYPE_II',
        name: 'Logical Access Controls',
        description: 'Access to cloud infrastructure is restricted and authenticated.',
        status: 'VERIFIED',
        satisfying_artifact: 'policy',
        claim_details: 'Automated Rego guardrail enforces role-based session timeouts and MFA.',
      },
      {
        id: 'CC6.8',
        framework: 'SOC2_TYPE_II',
        name: 'Unauthorized Software & Changes Prevention',
        description: 'Prevent unauthorized drift or deployment of unsafe configurations.',
        status: 'VERIFIED',
        satisfying_artifact: 'iac',
        claim_details: 'Terraform remediation patch locks S3 bucket ACLs and enforces server-side KMS encryption.',
      },
    ],
    cis_benchmarks: [
      {
        id: 'CIS-1.4',
        framework: 'CIS_BENCHMARK',
        name: 'Ensure root user has no active access keys',
        description: 'Root access must be restricted to break-glass procedures.',
        status: 'VERIFIED',
        satisfying_artifact: 'policy',
        claim_details: 'Policy denies actions executed directly using root account credentials.',
      },
    ],
    audit_notes: 'All generated guardrails strictly adhere to SOC 2 Type II trust criteria and CIS Cloud Foundations Benchmark.',
    generated_at: new Date().toISOString(),
  };
}

// ─── Export API object ────────────────────────────────────────────────────────
export const cirusAPI = {
  getIncidents,
  getIncident,
  getArtifacts,
  regenerateArtifact,
  createIncident,
  deleteIncident,
  getWorkflowRun,
  getWorkflowRunByIncident,
  getRiskScore,
  getExtraction,
  getDashboardStats,
  createGitOpsPR,
  getIncidentCompliance,
};

export type { CirusAPIError };

export async function fetchDashboardData() {
  if (process.env.NEXT_PUBLIC_USE_MOCKS === 'true') {
    await new Promise(r => setTimeout(r, 800));
    return {
      kpis: [
        { title: "Total Incidents", value: "142", icon: "Activity" },
        { title: "Active Guardrails", value: "48", icon: "Shield" },
        { title: "Risk Reduction", value: "34%", icon: "TrendingDown" },
        { title: "Avg. Resolution Time", value: "45m", icon: "Clock" },
      ],
      chartData: [
        { name: "Mon", before: 80, after: 30 },
        { name: "Tue", before: 75, after: 25 },
        { name: "Wed", before: 82, after: 28 },
        { name: "Thu", before: 78, after: 22 },
        { name: "Fri", before: 85, after: 35 },
        { name: "Sat", before: 70, after: 20 },
        { name: "Sun", before: 72, after: 18 },
      ],
      incidents: [
        { id: "inc-101", title: "DB Connection Pool Exhaustion", provider: "AWS", severity: "CRITICAL", riskDelta: 45, status: "completed" },
        { id: "inc-102", title: "K8s OOMKill on Ingress", provider: "GCP", severity: "HIGH", riskDelta: 30, status: "ready" },
        { id: "inc-103", title: "Redis Cache Eviction Spike", provider: "Azure", severity: "MEDIUM", riskDelta: 15, status: "processing" },
      ]
    };
  }

  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const apiKey = process.env.NEXT_PUBLIC_API_KEY || 'dev-api-key-12345';
  const headers: Record<string, string> = { 'X-API-Key': apiKey };

  try {
    const [statsRes, incidentsRes] = await Promise.all([
      fetch(`${baseUrl}/api/v1/dashboard/stats`, { headers, cache: 'no-store' }),
      fetch(`${baseUrl}/api/v1/incidents/?limit=10`, { headers, cache: 'no-store' }),
    ]);

    if (!statsRes.ok || !incidentsRes.ok) {
      throw new Error(`Backend responded with error: stats=${statsRes.status} incidents=${incidentsRes.status}`);
    }

    const stats = await statsRes.json();
    const incidentsList = await incidentsRes.json();

    return {
      kpis: [
        { title: "Total Incidents",    value: String(stats.total_incidents    ?? 0), icon: "Activity"    },
        { title: "Active Guardrails",  value: String(stats.guardrails_generated ?? 0), icon: "Shield"   },
        { title: "Risk Reduction",     value: `${stats.avg_risk_reduction ?? 0}%`,    icon: "TrendingDown" },
        { title: "Awaiting Approval",  value: String(stats.awaiting_approval   ?? 0), icon: "Clock"     },
      ],
      chartData: (stats.risk_trend ?? []).map((t: { date: string; avg_risk_before: number; avg_risk_after: number }) => ({
        name: t.date,
        before: t.avg_risk_before,
        after: t.avg_risk_after,
      })),
      incidents: (incidentsList.items ?? []).map((i: { id: string; title: string; provider: string; severity: string; risk_score?: { delta: number }; status: string }) => ({
        id: i.id,
        title: i.title,
        provider: i.provider,
        severity: i.severity,
        riskDelta: i.risk_score?.delta ?? 0,
        status: i.status,
      })),
    };
  } catch (err) {
    // Backend unreachable — return empty state so the page still renders
    console.warn('[fetchDashboardData] Backend unavailable, using empty state:', (err as Error).message);
    return {
      kpis: [
        { title: "Total Incidents",   value: "—", icon: "Activity"     },
        { title: "Active Guardrails", value: "—", icon: "Shield"       },
        { title: "Risk Reduction",    value: "—", icon: "TrendingDown" },
        { title: "Awaiting Approval", value: "—", icon: "Clock"        },
      ],
      chartData: [],
      incidents: [],
    };
  }
}
