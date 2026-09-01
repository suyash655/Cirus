'use client';

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import type { RiskTrendPoint } from '@/lib/types';

export function RiskTrendChart({ data }: { data: RiskTrendPoint[] }) {
  const chartData = data.map((p) => ({
    date: p.date,
    before: p.avgRiskBefore,
    after: p.avgRiskAfter,
  }));

  return (
    <section
      className="rounded-[12px] p-6"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
      }}
    >
      <div className="flex items-center justify-between mb-1">
        <h2
          className="text-[14px] font-medium"
          style={{ color: 'var(--color-text-primary)' }}
        >
          Risk trend — last 7 days
        </h2>
        <span className="text-[12px]" style={{ color: 'var(--color-text-muted)' }}>
          avg risk score (0–100)
        </span>
      </div>
      <p className="text-[13px] mb-4" style={{ color: 'var(--color-text-muted)' }}>
        Average risk score before and after guardrail application.
      </p>

      {chartData.length === 0 ? (
        <div
          className="h-[240px] flex items-center justify-center text-[13px]"
          style={{ color: 'var(--color-text-muted)' }}
        >
          No completed runs yet — trend will appear once incidents are processed.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-border)"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 12, fill: 'var(--color-text-muted)' }}
              axisLine={false}
              tickLine={false}
              width={32}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 8,
                border: '1px solid var(--color-border)',
                fontSize: 12,
                background: 'var(--color-surface)',
                color: 'var(--color-text-primary)',
                boxShadow: '0 8px 24px rgba(11,11,11,0.12)',
              }}
              formatter={(value: number, name: string) => [
                value.toFixed(1),
                name === 'before' ? 'Before remediation' : 'After remediation',
              ]}
            />
            <Legend
              formatter={(v) => (v === 'before' ? 'Before remediation' : 'After remediation')}
              wrapperStyle={{ fontSize: 12, paddingTop: 12, color: 'var(--color-text-secondary)' }}
            />
            <Line
              dataKey="before"
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={false}
              isAnimationActive
              animationDuration={800}
            />
            <Line
              dataKey="after"
              stroke="var(--color-success)"
              strokeWidth={2}
              dot={false}
              isAnimationActive
              animationDuration={800}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </section>
  );
}
