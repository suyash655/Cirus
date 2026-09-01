'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip } from 'recharts';

export function BarChartCard({ title, data }: { title: string; data: { category: string; count: number }[] }) {
  return <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-md)] p-6">
    <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} layout="vertical" margin={{ top: 12, right: 12, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }} axisLine={false} tickLine={false} allowDecimals={false} />
        <YAxis type="category" dataKey="category" tick={{ fontSize: 12, fill: 'var(--color-text-primary)' }} axisLine={false} tickLine={false} width={110} />
        <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid var(--color-border)', fontSize: 12, background: 'var(--color-surface)' }} />
        <Bar dataKey="count" fill="var(--color-accent)" radius={[0, 4, 4, 0]} animationDuration={700} isAnimationActive />
      </BarChart>
    </ResponsiveContainer>
  </section>;
}
