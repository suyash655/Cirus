'use client';

import Link from 'next/link';
import { AlertTriangle, Clock, ShieldCheck, TrendingDown } from 'lucide-react';
import { useDashboardStats, useIncidents } from '@/lib/hooks/use-incidents';
import { RiskTrendChart } from '@/components/dashboard/RiskTrendChart';
import { GuardrailReviewQueue } from '@/components/dashboard/GuardrailReviewQueue';
import { MTTGGauge } from '@/components/dashboard/MTTGGauge';

// ─── Loading skeleton for a metric tile ──────────────────────────────────────
function TileSkeleton() {
  return (
    <div
      className="rounded-[12px] p-6"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        height: 140,
      }}
    >
      <div className="c-skeleton h-3 w-24 mb-4" />
      <div className="c-skeleton h-8 w-16 mb-2" />
      <div className="c-skeleton h-3 w-20" />
    </div>
  );
}

// ─── Metric tile ──────────────────────────────────────────────────────────────
type TileState = 'loading' | 'empty' | 'ready';

function MetricTile({
  label,
  state = 'ready',
  value,
  delta,
  children,
  onClick,
}: {
  label: string;
  state?: TileState;
  value?: number | string;
  delta?: string;
  children?: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <div
      className={onClick ? 'c-card-interactive' : 'c-metric-tile'}
      onClick={onClick}
      style={{ minHeight: 140 }}
    >
      <span className="c-metric-label">{label}</span>

      {state === 'loading' && (
        <div>
          <div className="c-skeleton h-8 w-16 mt-2 mb-1" />
          <div className="c-skeleton h-3 w-20" />
        </div>
      )}

      {state === 'empty' && (
        <p className="mt-2 text-[13px]" style={{ color: 'var(--color-text-muted)' }}>
          No data yet
        </p>
      )}

      {state === 'ready' && children}

      {state === 'ready' && value !== undefined && !children && (
        <>
          <p className="c-metric-value tabular-nums">{value}</p>
          {delta && <p className="c-metric-delta">{delta}</p>}
        </>
      )}
    </div>
  );
}

// ─── Dashboard page ───────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: incidents = [], isLoading: incidentsLoading } = useIncidents();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const loading = incidentsLoading || statsLoading;

  const ready    = incidents.filter((i) => i.status === 'ready');
  const awaiting = ready;
  const mttgHours = stats?.mttgHours ?? 0;

  const tileState: TileState = loading ? 'loading' : 'ready';

  return (
    <div className="max-w-[1200px] mx-auto">
      {/* ── Page header ────────────────────────────────────────────────────── */}
      <header className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <p
            className="text-[13px] font-normal mb-1"
            style={{ color: 'var(--color-text-secondary)', letterSpacing: '0.02em' }}
          >
            Operations overview
          </p>
          <h1
            className="text-[20px] font-medium"
            style={{ color: 'var(--color-text-primary)' }}
          >
            CIRUS Dashboard
          </h1>
        </div>
      </header>

      {/* ── Metric strip ───────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Hero metric — incidents this period (gets the big number treatment) */}
        <div
          className="c-metric-tile sm:col-span-2 lg:col-span-1"
          style={{ minHeight: 140 }}
        >
          <span className="c-metric-label">Incidents this period</span>
          {loading ? (
            <div className="c-skeleton h-12 w-20 mt-2" />
          ) : (
            <>
              <p className="c-metric-value-hero tabular-nums mt-2">
                {stats?.totalIncidents ?? incidents.length}
              </p>
              <p className="c-metric-delta mt-1">↑ 8% vs last period</p>
            </>
          )}
        </div>

        {/* MTTG */}
        <MetricTile
          label="Mean time to guardrail"
          state={tileState}
        >
          {mttgHours > 0 ? (
            <MTTGGauge hours={mttgHours} />
          ) : (
            <p
              className="mt-2 text-[24px] font-medium tabular-nums"
              style={{ color: 'var(--color-text-primary)' }}
            >
              —
            </p>
          )}
        </MetricTile>

        {/* Guardrails merged */}
        <MetricTile
          label="Guardrails generated"
          state={tileState}
          value={stats?.guardrailsGenerated ?? ready.length}
          delta="↑ 12% vs last period"
        />

        {/* Awaiting approval */}
        <MetricTile
          label="Awaiting approval"
          state={tileState}
          value={stats?.awaitingApproval ?? awaiting.length}
          onClick={() =>
            document.getElementById('guardrail-review-queue')?.scrollIntoView({ behavior: 'smooth' })
          }
        />
      </div>

      {/* ── Risk Trend Chart ────────────────────────────────────────────────── */}
      <div className="mt-8">
        {loading ? (
          <div
            className="rounded-[12px] animate-pulse"
            style={{
              height: 320,
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
            }}
          />
        ) : (
          <RiskTrendChart data={stats?.riskTrend ?? []} />
        )}
      </div>

      {/* ── Guardrail Review Queue ──────────────────────────────────────────── */}
      <GuardrailReviewQueue incidents={awaiting} />
    </div>
  );
}
