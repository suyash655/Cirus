'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useDashboardStats } from '@/lib/hooks/use-incidents';

// Resolved vs artifacts generated (grouped bar)
const MOCK_RESOLVED = [
  { month: 'Apr', resolved: 4, artifacts: 18 },
  { month: 'May', resolved: 7, artifacts: 29 },
  { month: 'Jun', resolved: 5, artifacts: 21 },
  { month: 'Jul', resolved: 9, artifacts: 38 },
  { month: 'Aug', resolved: 6, artifacts: 24 },
  { month: 'Sep', resolved: 3, artifacts: 13 },
];

// Risk exposure by service (horizontal bar)
const MOCK_SERVICES = [
  { service: 'payments-api', risk: 82 },
  { service: 'auth-service',  risk: 71 },
  { service: 'data-pipeline', risk: 60 },
  { service: 'cdn-proxy',     risk: 48 },
  { service: 'billing-cron',  risk: 37 },
];

// Artifact type breakdown
const MOCK_ARTIFACT_BREAKDOWN = [
  { type: 'RCA',        count: 12 },
  { type: 'Policy',     count: 9  },
  { type: 'IaC',        count: 11 },
  { type: 'Alerts',     count: 8  },
  { type: 'Runbook',    count: 10 },
  { type: 'Regression', count: 6  },
];

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-[14px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
        {title}
      </h2>
      {subtitle && (
        <p className="text-[13px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  const { data: stats } = useDashboardStats();

  // KPI tiles
  const kpis = [
    { label: 'Total incidents',     value: stats?.totalIncidents    ?? '—' },
    { label: 'Guardrails generated',value: stats?.guardrailsGenerated ?? '—' },
    { label: 'Avg risk reduction',  value: stats ? `${stats.avgRiskReduction}%` : '—' },
    { label: 'Awaiting approval',   value: stats?.awaitingApproval  ?? '—' },
  ];

  return (
    <div className="max-w-[1200px] mx-auto">
      <header className="mb-8">
        <p
          className="text-[13px] mb-1"
          style={{ color: 'var(--color-text-secondary)', letterSpacing: '0.02em' }}
        >
          Performance overview
        </p>
        <h1 className="text-[20px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
          Analytics
        </h1>
      </header>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="rounded-[12px] p-6"
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
          >
            <span className="c-metric-label">{kpi.label}</span>
            <p className="c-metric-value tabular-nums mt-2">{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Two-column chart row */}
      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        {/* Resolved vs artifacts generated (grouped bar) */}
        <div
          className="rounded-[12px] p-6"
          style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
        >
          <SectionHeader
            title="Incidents resolved vs. artifacts generated"
            subtitle="Monthly comparison"
          />
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={MOCK_RESOLVED} barGap={4} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
              <XAxis dataKey="month" tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} width={28} />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: '1px solid var(--color-border)',
                  fontSize: 12,
                  background: 'var(--color-surface)',
                  boxShadow: '0 8px 24px rgba(11,11,11,0.12)',
                }}
              />
              <Bar dataKey="resolved"  name="Incidents resolved"    fill="var(--color-accent)"  radius={[4,4,0,0]} />
              <Bar dataKey="artifacts" name="Artifacts generated"   fill="var(--color-success)" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Risk exposure by service (horizontal bar) */}
        <div
          className="rounded-[12px] p-6"
          style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
        >
          <SectionHeader
            title="Risk exposure by service"
            subtitle="Current risk score (0–100)"
          />
          <ResponsiveContainer width="100%" height={240}>
            <BarChart
              data={MOCK_SERVICES}
              layout="vertical"
              margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }} axisLine={false} tickLine={false} />
              <YAxis
                type="category"
                dataKey="service"
                tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }}
                axisLine={false}
                tickLine={false}
                width={100}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 8,
                  border: '1px solid var(--color-border)',
                  fontSize: 12,
                  background: 'var(--color-surface)',
                  boxShadow: '0 8px 24px rgba(11,11,11,0.12)',
                }}
              />
              <Bar dataKey="risk" name="Risk score" radius={[0, 4, 4, 0]} isAnimationActive animationDuration={700}>
                {MOCK_SERVICES.map((entry) => (
                  <Cell
                    key={entry.service}
                    fill={entry.risk >= 70 ? 'var(--color-danger)' : entry.risk >= 50 ? 'var(--color-warning)' : 'var(--color-accent)'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Artifact type breakdown (stacked horizontal bars — no pie) */}
      <div
        className="rounded-[12px] p-6"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        <SectionHeader title="Artifact type breakdown" subtitle="Total generated per type" />
        <div className="flex flex-col gap-3 mt-4">
          {MOCK_ARTIFACT_BREAKDOWN.map((item) => {
            const max = Math.max(...MOCK_ARTIFACT_BREAKDOWN.map((x) => x.count));
            const pct = (item.count / max) * 100;
            return (
              <div key={item.type} className="flex items-center gap-3">
                <span
                  className="w-20 text-[13px] text-right flex-shrink-0"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  {item.type}
                </span>
                <div
                  className="flex-1 rounded-full overflow-hidden"
                  style={{ height: 8, background: 'var(--color-bg)' }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${pct}%`, background: 'var(--color-accent)' }}
                  />
                </div>
                <span
                  className="w-6 text-[13px] tabular-nums text-right"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  {item.count}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
