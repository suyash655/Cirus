'use client';

import { use } from 'react';
import Link from 'next/link';
import { ArrowLeft, CheckCircle2, AlertTriangle, Clock, Loader2, RefreshCw, Copy, Check } from 'lucide-react';
import { useIncident, useArtifacts, useRiskScore } from '@/lib/hooks/use-incidents';
import { useWorkflowRunByIncident } from '@/lib/hooks/use-workflow';
import { WorkflowTracker } from '@/components/WorkflowTracker';
import { ArtifactTabs } from '@/components/ArtifactTabs';
import { ComplianceAuditCard } from '@/components/incident/compliance-audit-card';
import { GroundedClaimBadge } from '@/components/incident/grounded-claim-badge';
import { formatRelativeTime } from '@/lib/utils';
import { useState } from 'react';

// ─── Severity pill ────────────────────────────────────────────────────────────
function SevPill({ sev }: { sev: string }) {
  const cls = sev === 'P1' ? 'c-sev-p1' : sev === 'P2' ? 'c-sev-p2' : sev === 'P3' ? 'c-sev-p3' : 'c-sev-p4';
  return <span className={cls}>{sev}</span>;
}

// ─── Status pill ──────────────────────────────────────────────────────────────
function StatusPill({ status }: { status: string }) {
  const map: Record<string, { cls: string; icon: React.ReactNode; label: string }> = {
    processing: { cls: 'c-pill-processing', icon: <Loader2 className="w-3 h-3 animate-spin" />, label: 'Processing' },
    ready:      { cls: 'c-pill-ready',      icon: <CheckCircle2 className="w-3 h-3" />,         label: 'Ready' },
    error:      { cls: 'c-pill-error',      icon: <AlertTriangle className="w-3 h-3" />,        label: 'Error' },
    partial:    { cls: 'c-pill-partial',    icon: <Clock className="w-3 h-3" />,                label: 'Partial' },
  };
  const cfg = map[status] ?? map.processing;
  return (
    <span className={cfg.cls}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

// ─── Inline risk stat ─────────────────────────────────────────────────────────
function InlineRisk({ incidentId }: { incidentId: string }) {
  const { data: risk } = useRiskScore(incidentId);
  if (!risk) return null;
  return (
    <div
      className="inline-flex items-center gap-3 px-3 py-1.5 rounded-md text-[12px]"
      style={{
        background: 'var(--color-success-bg)',
        border: '1px solid rgba(15,110,86,0.2)',
      }}
    >
      <span style={{ color: 'var(--color-text-secondary)' }}>Risk:</span>
      <span style={{ color: 'var(--color-danger)', fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>
        {risk.beforeRemediation}
      </span>
      <span style={{ color: 'var(--color-text-muted)' }}>→</span>
      <span style={{ color: 'var(--color-success)', fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>
        {risk.afterRemediation}
      </span>
      <span style={{ color: 'var(--color-success)' }}>−{risk.delta} pts</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [copied, setCopied] = useState(false);

  const { data: incident, isLoading, isError, refetch } = useIncident(id);

  const handleCopyId = async () => {
    await navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto flex flex-col items-center justify-center min-h-64 gap-4">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--color-accent)' }} />
        <p className="text-[13px]" style={{ color: 'var(--color-text-muted)' }}>Loading incident…</p>
      </div>
    );
  }

  if (isError || !incident) {
    return (
      <div className="max-w-4xl mx-auto flex flex-col items-center justify-center min-h-64 gap-4">
        <AlertTriangle className="w-6 h-6" style={{ color: 'var(--color-danger)' }} />
        <p className="text-[13px]" style={{ color: 'var(--color-text-muted)' }}>Incident not found.</p>
        <div className="flex gap-3">
          <button onClick={() => refetch()} className="c-btn-secondary c-btn-sm">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
          <Link href="/dashboard" className="c-btn-secondary c-btn-sm inline-flex items-center gap-1.5">
            <ArrowLeft className="w-3 h-3" /> Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const isProcessing = incident.status === 'processing';

  return (
    <div className="max-w-4xl mx-auto pb-12">
      {/* Back */}
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 text-[13px] mb-6 transition-colors"
        style={{ color: 'var(--color-text-muted)' }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--color-text-primary)')}
        onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--color-text-muted)')}
      >
        <ArrowLeft className="w-3.5 h-3.5" /> All Incidents
      </Link>

      {/* ── Banner ─────────────────────────────────────────────────────────── */}
      <div
        className="rounded-[12px] p-6 mb-6 relative"
        style={{
          background: 'var(--color-surface)',
          border: '2px solid var(--color-border-strong)',
        }}
      >
        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <StatusPill status={incident.status} />
          <SevPill sev={incident.severity} />
          <span
            className="c-pill"
            style={{
              background: 'var(--color-bg)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-secondary)',
            }}
          >
            {incident.provider}
          </span>

          {/* Risk inline stat (demoted from slab to compact) */}
          {incident.status === 'ready' && <InlineRisk incidentId={id} />}

          {/* Evidence Grounding & Anti-Hallucination verification */}
          {incident.status === 'ready' && <GroundedClaimBadge incidentId={id} />}
        </div>

        {/* Title */}
        <h1
          className="text-[20px] font-medium leading-snug mb-2"
          style={{ color: 'var(--color-text-primary)' }}
        >
          {incident.title}
        </h1>

        {incident.summary && (
          <p
            className="text-[14px] leading-relaxed max-w-2xl"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            {incident.summary}
          </p>
        )}

        {/* Footer meta */}
        <div
          className="flex items-center gap-3 mt-4 flex-wrap text-[12px]"
          style={{ color: 'var(--color-text-muted)' }}
        >
          <button
            onClick={handleCopyId}
            className="flex items-center gap-1.5 transition-colors font-mono"
            title="Copy incident ID"
            onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--color-text-primary)')}
            onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = 'var(--color-text-muted)')}
          >
            {copied ? <Check className="w-3 h-3" style={{ color: 'var(--color-success)' }} /> : <Copy className="w-3 h-3" />}
            {id}
          </button>
          <span>·</span>
          <span>{formatRelativeTime(incident.updatedAt)}</span>
          {incident.artifactsReady.length > 0 && (
            <>
              <span>·</span>
              <span style={{ color: 'var(--color-success)', fontWeight: 500 }}>
                {incident.artifactsReady.length} artifact{incident.artifactsReady.length !== 1 ? 's' : ''} ready
              </span>
            </>
          )}
        </div>
      </div>

      {/* ── Pipeline stepper ────────────────────────────────────────────────── */}
      <WorkflowTracker incidentId={id} />

      {/* ── Verified SOC Claims & Audit Card ───────────────────────────────── */}
      {!isProcessing && <ComplianceAuditCard incidentId={id} />}

      {/* ── Artifacts ───────────────────────────────────────────────────────── */}
      {!isProcessing && (
        <div className="mt-6" style={{ position: 'relative' }}>
          <h2
            className="text-[14px] font-medium mb-4"
            style={{ color: 'var(--color-text-primary)' }}
          >
            Generated artifacts
          </h2>
          <ArtifactTabs incidentId={id} />
        </div>
      )}

      {/* Processing state */}
      {isProcessing && (
        <div
          className="mt-6 rounded-[12px] p-10 flex flex-col items-center justify-center text-center gap-3"
          style={{
            border: '1px dashed var(--color-border-strong)',
            background: 'var(--color-surface)',
          }}
        >
          <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--color-accent)' }} />
          <p className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
            AI pipeline is running…
          </p>
          <p className="text-[13px]" style={{ color: 'var(--color-text-muted)' }}>
            Artifacts will appear here once all stages complete. Usually 30–60 seconds.
          </p>
        </div>
      )}
    </div>
  );
}
