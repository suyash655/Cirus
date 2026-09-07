'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Zap, Radio, Copy, Check, Sparkles } from 'lucide-react';
import { useCreateIncident } from '@/lib/hooks/use-incidents';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/shared/page-header';
import { ARTIFACT_META, cn, detectFormat } from '@/lib/utils';
import type { ArtifactType, CloudProvider, Severity } from '@/lib/types';
import { ProviderSelector } from '@/components/incident/ProviderSelector';
import { SeveritySelector } from '@/components/incident/SeveritySelector';
import { UploadDropzone } from '@/components/incident/UploadDropzone';

// ─── Artifact picker ──────────────────────────────────────────────────────────
function ArtifactPicker({
  selected, onChange,
}: { selected: ArtifactType[]; onChange: (v: ArtifactType[]) => void }) {
  const toggle = (t: ArtifactType) => {
    onChange(selected.includes(t) ? selected.filter(x => x !== t) : [...selected, t]);
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {(Object.keys(ARTIFACT_META) as ArtifactType[]).map((type) => {
        const meta = ARTIFACT_META[type];
        const isSelected = selected.includes(type);
        return (
          <button
            key={type}
            type="button"
            id={`artifact-${type}`}
            onClick={() => toggle(type)}
            className="flex items-center gap-2.5 p-3 rounded-xl text-left transition-all duration-150"
            style={{
              background: isSelected ? 'hsl(var(--bg-raised))' : 'hsl(var(--bg-surface))',
              border: `1px solid ${isSelected ? 'hsl(var(--border-strong))' : 'hsl(var(--border-base))'}`,
            }}
          >
            <span className="text-lg">{meta.emoji}</span>
            <div className="min-w-0">
              <p className="text-xs font-semibold" style={{ color: isSelected ? 'hsl(var(--text-primary))' : 'hsl(var(--text-secondary))' }}>
                {meta.shortLabel}
              </p>
              <p className="text-[10px] text-text-muted truncate">{meta.fileExt}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ─── Processing animation ─────────────────────────────────────────────────────
const PROCESSING_STEPS = [
  { label: 'Queued' },
  { label: 'Normalizing incident data…' },
  { label: 'Classifying root cause…' },
  { label: 'Enriching context…' },
  { label: 'Generating artifacts…' },
  { label: 'Validating outputs…' },
  { label: 'Ready for review' },
];

const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

function ProcessingOverlay({ step }: { step: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-2xl gap-6"
      style={{ background: 'hsl(var(--bg-surface) / 0.96)', backdropFilter: 'blur(8px)' }}
    >
      <div className="w-14 h-14 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-text-primary animate-spin" />
      </div>
      <div className="flex flex-col items-center gap-2">
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="text-sm font-medium text-text-primary"
          >
            {PROCESSING_STEPS[step % PROCESSING_STEPS.length].label}
          </motion.p>
        </AnimatePresence>
        <p className="text-xs text-text-muted">Processing your incident report…</p>
      </div>
      <div className="flex items-center gap-1.5">
        {PROCESSING_STEPS.map((_, i) => (
          <div
            key={i}
            className="h-1 rounded-full transition-all duration-500"
            style={{
              width: i === step % PROCESSING_STEPS.length ? 24 : 6,
              background: i === step % PROCESSING_STEPS.length ? 'hsl(var(--text-primary))' : 'hsl(var(--border-strong))',
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}

// ─── Incident presets ────────────────────────────────────────────────────────
const INCIDENT_PRESETS = [
  {
    label: 'S3 Data Exposure',
    emoji: '🪣',
    provider: 'AWS' as CloudProvider,
    severity: 'P2' as Severity,
    title: 'AWS S3 Public Bucket Exposure — Production Assets',
    rawText: `[CRITICAL] S3 bucket 'prod-assets-backup' was detected as publicly accessible via AWS Config rule 's3-bucket-public-read-prohibited'.

Timestamp: 2026-09-07T06:14:31Z
Bucket: prod-assets-backup (us-east-1)
ACL: public-read
Objects exposed: ~4,200 files including PII CSV exports
Impacted services: report-generator, customer-portal, billing-service

Root cause: IAM permission misconfiguration applied during automation pipeline run (PR #3811). s3:PutBucketAcl was granted to CI service account without restriction.

Immediate action: CloudTrail events show 18 external IP reads in 47-minute exposure window.`,
    artifacts: ['policy', 'iac', 'runbook', 'rca'] as ArtifactType[],
  },
  {
    label: 'K8s OOMKilled',
    emoji: '☸️',
    provider: 'GCP' as CloudProvider,
    severity: 'P2' as Severity,
    title: 'Kubernetes Ingress Controller OOMKilled — GKE Production',
    rawText: `[ALERT] ingress-nginx pod crashed with OOMKilled signal on GKE cluster 'prod-us-central1-1'.

Timestamp: 2026-09-07T09:42:05Z
Namespace: ingress-nginx
Pod: ingress-nginx-controller-7d4d7b9b9d-hqz2x
Exit Code: 137 (OOMKilled)
Crashes (last 2h): 14 (CrashLoopBackOff)
Memory limit: 256Mi — Usage at spike: 498Mi

Impacted: All external traffic routed through ingress. 3 customer-facing services degraded for ~18 minutes.
Related: Recent deployment of log-injection middleware (commit a7fc331) added unbounded in-memory buffering.`,
    artifacts: ['rca', 'iac', 'alerts', 'runbook'] as ArtifactType[],
  },
  {
    label: 'RDS Pool Exhaustion',
    emoji: '🗄️',
    provider: 'AWS' as CloudProvider,
    severity: 'P1' as Severity,
    title: 'RDS PostgreSQL Connection Pool Exhaustion — API Gateway',
    rawText: `[P1] Production RDS instance 'api-db-prod' hit max_connections limit (500/500).

Timestamp: 2026-09-07T14:20:00Z
DB: api-db-prod (PostgreSQL 16, db.r6g.2xlarge)
Error: FATAL: remaining connection slots are reserved for non-replication superuser connections
Affected: api-gateway (all replicas), user-service, payment-service
Duration: 23 minutes (14:20 - 14:43 UTC)

SLO breach: 99.9% → 98.1% for that window.
Root cause: connection pool misconfiguration after worker count scaling (max_overflow=0 removed). ~12,000 requests returned HTTP 503.`,
    artifacts: ['rca', 'policy', 'iac', 'alerts'] as ArtifactType[],
  },
  {
    label: 'IAM Escalation',
    emoji: '🔐',
    provider: 'AWS' as CloudProvider,
    severity: 'P1' as Severity,
    title: 'CloudTrail IAM Privilege Escalation Detected',
    rawText: `[SECURITY] CloudTrail detected a privilege escalation chain for IAM user 'svc-deploy-runner'.

Timestamp: 2026-09-07T03:11:47Z
Event chain:
  1. iam:CreatePolicyVersion → new inline policy attached with sts:AssumeRole *
  2. sts:AssumeRole → assumed role 'arn:aws:iam::123456789012:role/OrganizationAccountAccessRole'
  3. iam:AttachUserPolicy → AdministratorAccess attached to 'svc-deploy-runner'

Source IP: 203.0.113.45 (unknown external IP)
User agent: aws-cli/2.13.0
Region: us-east-1

Status: IAM user suspended. Keys rotated. Incident declared P1. Forensic analysis required.`,
    artifacts: ['rca', 'policy', 'runbook', 'regression'] as ArtifactType[],
  },
] as const;

// ─── Main form ────────────────────────────────────────────────────────────────
export default function NewIncidentPage() {
  const router = useRouter();
  const { mutateAsync: createIncident, isPending } = useCreateIncident();
  const [processingStep, setProcessingStep] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const [form, setForm] = useState({
    title: '',
    rawText: '',
    provider: 'AWS' as CloudProvider,
    severity: 'P3' as Severity,
    selectedArtifacts: Object.keys(ARTIFACT_META) as ArtifactType[],
    affectedServices: '',
    configSnippet: '',
    inputMethod: 'paste' as 'paste' | 'upload',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const applyPreset = (preset: typeof INCIDENT_PRESETS[number]) => {
    setForm((f) => ({
      ...f,
      title: preset.title,
      rawText: preset.rawText,
      provider: preset.provider,
      severity: preset.severity,
      selectedArtifacts: [...preset.artifacts],
      inputMethod: 'paste',
    }));
    setErrors({});
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.title.trim()) e.title = 'Incident title is required';
    if (!form.rawText.trim()) e.rawText = 'Incident report text is required';
    if (form.selectedArtifacts.length === 0) e.artifacts = 'Select at least one artifact type';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsProcessing(true);

    // Animate processing steps
    const stepInterval = setInterval(() => {
      setProcessingStep((p) => p + 1);
    }, 700);

    try {
      const { id } = await createIncident({
        title: form.title,
        rawText: form.rawText,
        inputMethod: form.inputMethod,
        selectedArtifacts: form.selectedArtifacts,
        provider: form.provider,
        severity: form.severity,
      });
      clearInterval(stepInterval);
      setTimeout(() => router.push(`/incidents/${id}`), 600);
    } catch {
      clearInterval(stepInterval);
      setIsProcessing(false);
    }
  };

  const [copiedWebhook, setCopiedWebhook] = useState<string | null>(null);

  const copyUrl = (type: string, url: string) => {
    navigator.clipboard.writeText(url);
    setCopiedWebhook(type);
    setTimeout(() => setCopiedWebhook(null), 2000);
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] px-8 py-10 max-w-[900px] mx-auto">
      <PageHeader
        title="New Incident"
        description="Provide your incident report or connect automated webhooks to generate prevention artifacts."
      />

      {/* Webhook live ingestion snippet */}
      <div
        className="mb-8 p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-purple-500/10 text-purple-400">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <p className="text-[13px] font-medium text-text-primary">Automated Alert Ingestion Webhooks</p>
            <p className="text-[12px] text-text-muted">Auto-trigger CIRUS remediation from PagerDuty & CloudWatch</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => copyUrl('pd', 'http://localhost:8000/api/v1/webhooks/pagerduty')}
            className="c-btn-secondary c-btn-sm text-[11px] font-mono flex items-center gap-1.5"
          >
            {copiedWebhook === 'pd' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            PagerDuty Webhook
          </button>
          <button
            type="button"
            onClick={() => copyUrl('cw', 'http://localhost:8000/api/v1/webhooks/cloudwatch')}
            className="c-btn-secondary c-btn-sm text-[11px] font-mono flex items-center gap-1.5"
          >
            {copiedWebhook === 'cw' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            CloudWatch SNS
          </button>
        </div>
      </div>

      {/* 1-click presets */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={13} style={{ color: 'var(--color-accent)' }} />
          <span className="text-[12px] font-medium" style={{ color: 'var(--color-text-secondary)' }}>Quick presets</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {INCIDENT_PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              id={`preset-${preset.label.replace(/\s+/g, '-').toLowerCase()}`}
              onClick={() => applyPreset(preset)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all duration-150 hover:scale-105"
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text-secondary)',
              }}
            >
              <span>{preset.emoji}</span>
              <span>{preset.label}</span>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded-full"
                style={{
                  background: preset.severity === 'P1' ? 'rgba(239,68,68,0.15)' : 'rgba(245,158,11,0.15)',
                  color: preset.severity === 'P1' ? '#ef4444' : '#f59e0b',
                }}
              >{preset.severity}</span>
            </button>
          ))}
        </div>
      </div>

      <motion.form variants={staggerContainer} initial="hidden" animate="show" onSubmit={handleSubmit} className="relative">
        <AnimatePresence>
          {isProcessing && <ProcessingOverlay step={processingStep} />}
        </AnimatePresence>

        <div className="flex flex-col gap-7">

          {/* ── Title ── */}
          <motion.section variants={staggerItem}>
            <Input
              id="incident-title"
              label="Incident Title *"
              placeholder="e.g. S3 Public Access Exposure in Prod"
              value={form.title}
              onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))}
              error={errors.title}
            />
          </motion.section>

          {/* ── Cloud provider ── */}
          <motion.section variants={staggerItem}>
            <label className="block text-sm font-semibold text-text-primary mb-3">
              Cloud Provider
            </label>
            <ProviderSelector value={form.provider} onChange={(v) => setForm(f => ({ ...f, provider: v }))} />
          </motion.section>

          {/* ── Severity ── */}
          <motion.section variants={staggerItem}>
            <label className="block text-sm font-semibold text-text-primary mb-3">
              Severity Level
            </label>
            <SeveritySelector value={form.severity} onChange={(v) => setForm(f => ({ ...f, severity: v }))} />
          </motion.section>

          {/* ── Incident text ── */}
          <motion.section variants={staggerItem}>
            <Textarea
              id="incident-text"
              label="Incident Report *"
              rows={10}
              placeholder="Paste your incident report here — CloudTrail logs, post-mortem notes, alert descriptions, or any free-form text…"
              value={form.rawText}
              onChange={(e) => setForm(f => ({ ...f, rawText: e.target.value }))}
              error={errors.rawText}
              hint={`${form.rawText.length} chars — Format detected: ${form.rawText ? detectFormat(form.rawText) : 'none'}`}
              showCharCount
              maxChars={50000}
              autoResize={false}
              style={{ minHeight: 220, fontFamily: 'monospace' }}
            />
            
            <div className="mt-4"><UploadDropzone onFile={(file) => { void file.text().then((text) => setForm((current) => ({ ...current, rawText: text || current.rawText || `Uploaded file: ${file.name}`, inputMethod: 'upload' }))); }} /></div>
          </motion.section>

          {/* ── Affected services ── */}
          <motion.section variants={staggerItem}>
            <Input
              id="affected-services"
              label="Affected Services (optional)"
              placeholder="e.g. S3, CloudFront, Lambda, RDS"
              value={form.affectedServices}
              onChange={(e) => setForm(f => ({ ...f, affectedServices: e.target.value }))}
              hint="Comma-separated list of services or resource names"
            />
          </motion.section>

          {/* ── Config snippet ── */}
          <motion.section variants={staggerItem}>
            <Textarea
              id="config-snippet"
              label="Terraform / Config Snippet (optional)"
              rows={6}
              placeholder="Paste relevant Terraform, CloudFormation, or config file content…"
              value={form.configSnippet}
              onChange={(e) => setForm(f => ({ ...f, configSnippet: e.target.value }))}
              hint="Helps generate more accurate IaC patches"
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </motion.section>

          {/* ── Artifact selection ── */}
          <motion.section variants={staggerItem}>
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-semibold text-text-primary">
                Artifact Types to Generate
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  id="select-all-artifacts"
                  onClick={() => setForm(f => ({ ...f, selectedArtifacts: Object.keys(ARTIFACT_META) as ArtifactType[] }))}
                  className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors"
                >
                  All
                </button>
                <span className="text-text-faint text-xs">·</span>
                <button
                  type="button"
                  id="clear-artifacts"
                  onClick={() => setForm(f => ({ ...f, selectedArtifacts: [] }))}
                  className="text-xs text-text-muted hover:text-danger transition-colors"
                >
                  None
                </button>
              </div>
            </div>
            <ArtifactPicker
              selected={form.selectedArtifacts}
              onChange={(v) => setForm(f => ({ ...f, selectedArtifacts: v }))}
            />
            {errors.artifacts && (
              <p className="text-xs text-danger mt-2">{errors.artifacts}</p>
            )}
          </motion.section>

          {/* ── Submit ── */}
          <div className="flex items-center gap-4 pt-2">
            <button
              type="submit"
              id="submit-incident"
              disabled={isPending || isProcessing}
              className="inline-flex items-center gap-2.5 font-semibold h-11 px-7 rounded-lg bg-inverse-bg text-inverse-text text-sm hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isPending || isProcessing ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing…</>
              ) : (
                <><Zap className="w-4 h-4" /> Analyze Incident</>
              )}
            </button>

            <button
              type="button"
              onClick={() => router.back()}
              className="text-sm text-text-muted hover:text-text-secondary transition-colors"
              id="cancel-incident"
            >
              Cancel
            </button>

            {form.selectedArtifacts.length > 0 && (
              <span className="text-xs text-text-faint ml-auto">
                {form.selectedArtifacts.length} artifact{form.selectedArtifacts.length !== 1 ? 's' : ''} selected
              </span>
            )}
          </div>
        </div>
      </motion.form>
    </div>
  );
}
