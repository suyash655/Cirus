// ═══════════════════════════════════════════
// CIRUS — Shared TypeScript Types
// ═══════════════════════════════════════════

export type Severity = 'P1' | 'P2' | 'P3' | 'P4';
export type CloudProvider = 'AWS' | 'GCP' | 'Azure' | 'Generic';
export type ArtifactType = 'rca' | 'policy' | 'iac' | 'alerts' | 'runbook' | 'regression';
export type IncidentStatus = 'processing' | 'ready' | 'error' | 'partial';
export type InputMethod = 'paste' | 'upload';

// ─── Incident ────────────────────────────────────────────────────────────────

export interface Incident {
  id: string;
  title: string;
  severity: Severity;
  provider: CloudProvider;
  status: IncidentStatus;
  createdAt: string; // ISO 8601
  updatedAt: string;
  summary: string;
  tags: string[];
  artifactsReady: ArtifactType[];
}

export interface IncidentDetail extends Incident {
  rawText: string;
  detectedFormat: 'json' | 'yaml' | 'markdown' | 'plain';
  timeline: TimelineEvent[];
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  title: string;
  description: string;
  type: 'detection' | 'impact' | 'mitigation' | 'resolution' | 'root-cause';
}

// ─── Artifacts ───────────────────────────────────────────────────────────────

export interface RCAArtifact {
  type: 'rca';
  executiveSummary: string;
  rootCause: string;
  contributingFactors: string[];
  impactAnalysis: {
    affectedSystems: string[];
    userImpact: string;
    dataScopingNote: string;
    estimatedDuration: string;
  };
  timeline: TimelineEvent[];
  lessonsLearned: string[];
  actionItems: ActionItem[];
}

export interface PolicyArtifact {
  type: 'policy';
  language: 'rego' | 'scp' | 'sentinel';
  description: string;
  code: string;
  tests: string;
  rationale: string;
  enforcement: 'deny' | 'warn' | 'audit';
}

export interface IaCArtifact {
  type: 'iac';
  tool: 'terraform' | 'cdk' | 'pulumi' | 'cloudformation';
  description: string;
  diff: string; // unified diff format
  fullPatch: string;
  affectedResources: string[];
  breakingChange: boolean;
}

export interface AlertsArtifact {
  type: 'alerts';
  provider: 'prometheus' | 'cloudwatch' | 'datadog' | 'generic';
  description: string;
  rules: AlertRule[];
}

export interface AlertRule {
  name: string;
  severity: 'critical' | 'warning' | 'info';
  expression: string;
  duration: string;
  labels: Record<string, string>;
  annotations: Record<string, string>;
}

export interface RunbookArtifact {
  type: 'runbook';
  title: string;
  description: string;
  prerequisites: string[];
  steps: RunbookStep[];
  escalation: string;
  references: string[];
}

export interface RunbookStep {
  id: number;
  title: string;
  description: string;
  command?: string;
  note?: string;
  severityGate?: Severity; // Only shown for this severity or above
  expectedOutput?: string;
}

export interface RegressionArtifact {
  type: 'regression';
  framework: 'pytest' | 'jest' | 'go-test' | 'junit';
  description: string;
  testCases: TestCase[];
}

export interface TestCase {
  id: string;
  name: string;
  description: string;
  category: 'positive' | 'negative' | 'boundary';
  code: string;
  expectedResult: string;
}

export type Artifact =
  | RCAArtifact
  | PolicyArtifact
  | IaCArtifact
  | AlertsArtifact
  | RunbookArtifact
  | RegressionArtifact;

export interface ArtifactSet {
  rca?: RCAArtifact;
  policy?: PolicyArtifact;
  iac?: IaCArtifact;
  alerts?: AlertsArtifact;
  runbook?: RunbookArtifact;
  regression?: RegressionArtifact;
}

// ─── Action Items ─────────────────────────────────────────────────────────────

export interface ActionItem {
  id: string;
  title: string;
  priority: 'high' | 'medium' | 'low';
  owner: string;
  dueDate: string;
  status: 'open' | 'in-progress' | 'done';
}

// ─── API Payloads ─────────────────────────────────────────────────────────────

export interface CreateIncidentPayload {
  title?: string;
  rawText: string;
  inputMethod: InputMethod;
  fileName?: string;
  selectedArtifacts: ArtifactType[];
  provider?: CloudProvider;
  severity?: Severity;
}

export interface CreateIncidentResponse {
  id: string;
  estimatedProcessingMs: number;
}

// ─── UI State ─────────────────────────────────────────────────────────────────

export interface ProcessingStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'done' | 'error';
  durationMs?: number;
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  description?: string;
  durationMs?: number;
}

// ─── Integration ──────────────────────────────────────────────────────────────

export interface Integration {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: 'cloud' | 'alerting' | 'devops' | 'communication';
  connected: boolean;
  configuredAt?: string;
}

// ─── Workflow Pipeline ───────────────────────────────────────────────────────

export type WorkflowStageId =
  | 'human-input'
  | 'normalization'
  | 'root-cause-classification'
  | 'context-enrichment'
  | 'artifact-generation'
  | 'validator-critic'
  | 'human-approval';

export type WorkflowRunStatus = 'queued' | 'running' | 'completed' | 'failed';
export type WorkflowStageStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';

export interface StageOutput {
  summary: string;
  data?: Record<string, unknown>;
  warnings?: string[];
  tokensUsed?: number;
  modelId?: string;
}

export interface WorkflowStage {
  id: WorkflowStageId | string;
  label: string;
  description: string;
  status: WorkflowStageStatus;
  startedAt?: string;
  completedAt?: string;
  durationMs?: number;
  output?: StageOutput;
  confidence?: number; // 0–1
  tokensUsed?: number;
  modelId?: string;
  logs?: string[];
}

export interface WorkflowRun {
  id: string;
  incidentId: string;
  status: WorkflowRunStatus;
  currentStage?: string;
  stages: WorkflowStage[];
  startedAt: string;
  updatedAt: string;
  completedAt?: string;
  totalTokensUsed?: number;
  modelId: string;
  triggeredBy: 'auto' | 'manual';
}

// ─── Risk Scoring ─────────────────────────────────────────────────────────────

export interface RiskDimension {
  score: number; // 0–100
  label: string;
  description: string;
}

export interface RiskScore {
  overall: number; // 0–100
  dimensions: {
    exposure: RiskDimension;
    blast_radius: RiskDimension;
    recurrence: RiskDimension;
    remediation_effort: RiskDimension;
  };
  beforeRemediation: number;
  afterRemediation: number;
  delta: number; // positive = improvement
  calculatedAt: string;
}

// ─── Confidence & Citations ───────────────────────────────────────────────────

export interface Citation {
  id: string;
  text: string;
  source: 'incident-text' | 'cloudtrail' | 'config-drift' | 'policy-doc' | 'runbook';
  relevance: number; // 0–1
  lineNumber?: number;
}

export interface ExtractionResult {
  title: string;
  detectedProvider: CloudProvider;
  detectedSeverity: Severity;
  affectedServices: string[];
  timeRange: { start: string; end: string };
  errorMessages: string[];
  structuredData: Record<string, unknown>;
  confidence: number; // 0–1
  citations: Citation[];
}

export interface APIKey {
  id: string;
  name: string;
  prefix: string;
  createdAt: string;
  lastUsedAt?: string;
  scopes: string[];
}

// ─── Dashboard Stats ──────────────────────────────────────────────────────────

export interface ArtifactSummary {
  policies: number;
  iacPatches: number;
  alerts: number;
  runbooks: number;
  regressionTests: number;
}

export interface RiskTrendPoint {
  date: string;        // e.g. "Mar 14"
  avgRiskBefore: number;
  avgRiskAfter: number;
}

export interface DashboardStats {
  totalIncidents: number;
  guardrailsGenerated: number;
  avgRiskReduction: number;     // percentage points
  awaitingApproval: number;
  artifactSummary: ArtifactSummary;
  riskTrend: RiskTrendPoint[];
  mttgHours: number;            // Mean Time to Guardrail in hours
}

// ─── Approval State ───────────────────────────────────────────────────────────

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'changes_requested';

export interface ApprovalState {
  incidentId: string;
  status: ApprovalStatus;
  comment?: string;
  reviewedBy?: string;
  reviewedAt?: string;
}

// ─── User Preferences ─────────────────────────────────────────────────────────

export interface UserPreference {
  userId: string;
  theme: 'dark' | 'system';
  sidebarCollapsed: boolean;
  defaultProvider: CloudProvider;
  defaultSeverity: Severity;
  notificationsEnabled: boolean;
}

// ─── Compliance & Verified SOC Claims ─────────────────────────────────────────

export interface ComplianceControl {
  id: string;
  framework: 'SOC2_TYPE_II' | 'CIS_BENCHMARK' | 'ISO_27001' | 'NIST_800_53';
  name: string;
  description: string;
  status: 'VERIFIED' | 'PARTIALLY_SATISFIED' | 'REMEDIATION_REQUIRED';
  satisfying_artifact: string;
  claim_details: string;
  evidence_citation?: string;
}

export interface IncidentComplianceReport {
  incident_id: string;
  overall_compliance_score: number;
  audit_readiness_status: 'AUDIT_READY' | 'ACTION_REQUIRED' | 'NON_COMPLIANT';
  verified_claims_count: number;
  soc2_controls: ComplianceControl[];
  cis_benchmarks: ComplianceControl[];
  audit_notes: string;
  generated_at: string;
}

// ─── GitOps ───────────────────────────────────────────────────────────────────

export interface CreatePRPayload {
  incidentId: string;
  targetRepo?: string;
  baseBranch?: string;
  title?: string;
  artifacts?: string[];
}

export interface GitOpsPRResult {
  success: boolean;
  prUrl: string;
  prNumber: number;
  branchName: string;
  targetRepo: string;
  filesCommitted: string[];
  commitSha: string;
  diffPreview: string;
  message: string;
  createdAt: string;
}


