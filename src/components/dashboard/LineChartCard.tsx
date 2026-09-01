'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function LineChartCard({ title, data, lines }: { title: string; data: Record<string, string | number>[]; lines: { key: string; color: string; label: string }[] }) {
  return <section className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-[var(--radius-md)] p-6">
    <h2 className="text-base font-semibold text-[var(--color-text-primary)]">{title}</h2>
    <div className="flex gap-4 mt-2 mb-4">{lines.map((line) => <span key={line.key} className="text-xs text-[var(--color-text-secondary)]"><i className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: line.color }} />{line.label}</span>)}</div>
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }} axisLine={false} tickLine={false} width={32} />
        <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid var(--color-border)', fontSize: 12, background: 'var(--color-surface)' }} />
        {lines.map((line) => <Line key={line.key} dataKey={line.key} stroke={line.color} strokeWidth={2} dot={false} isAnimationActive animationDuration={800} />)}
      </LineChart>
    </ResponsiveContainer>
  </section>;
}
