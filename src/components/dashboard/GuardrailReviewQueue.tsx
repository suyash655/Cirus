'use client';

import { useState, useMemo } from 'react';
import { Search, Filter } from 'lucide-react';
import type { Incident } from '@/lib/types';
import { QueueRow } from './QueueRow';

const SEVERITIES = ['All', 'P1', 'P2', 'P3', 'P4'] as const;
const PROVIDERS  = ['All', 'AWS', 'GCP', 'Azure', 'Kubernetes', 'Generic'] as const;

export function GuardrailReviewQueue({ incidents }: { incidents: Incident[] }) {
  const [visible,   setVisible]   = useState(incidents);
  const [severity,  setSeverity]  = useState<string>('All');
  const [provider,  setProvider]  = useState<string>('All');
  const [query,     setQuery]     = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return visible.filter((i) => {
      if (severity !== 'All' && i.severity !== severity) return false;
      if (provider !== 'All' && i.provider !== provider) return false;
      if (q && !i.title.toLowerCase().includes(q) && !i.summary.toLowerCase().includes(q) && !i.id.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [visible, severity, provider, query]);

  return (
    <section id="guardrail-review-queue" className="mt-8">
      {/* Header */}
      <div className="flex items-end justify-between mb-4">
        <div>
          <h2 className="text-[16px] font-medium" style={{ color: 'var(--color-text-primary)' }}>
            Guardrail review queue
          </h2>
          <p className="text-[13px] mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Review generated controls before they enter your codebase.
          </p>
        </div>
        <span className="text-[13px]" style={{ color: 'var(--color-text-muted)' }}>
          {filtered.length} awaiting approval
        </span>
      </div>

      {/* Filter bar */}
      <div
        className="mb-4 flex flex-wrap items-center gap-3 rounded-[10px] px-4 py-3"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        {/* Search */}
        <div className="relative flex-1 min-w-[180px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--color-text-muted)' }} />
          <input
            id="queue-search"
            type="text"
            placeholder="Search incidents…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full h-8 pl-8 pr-3 rounded-[6px] text-[12px] outline-none"
            style={{
              background: 'var(--color-bg)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)',
            }}
          />
        </div>

        {/* Severity pills */}
        <div className="flex items-center gap-1.5">
          <Filter size={12} style={{ color: 'var(--color-text-muted)' }} />
          {SEVERITIES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSeverity(s)}
              className="h-6 px-2.5 rounded-full text-[11px] font-medium transition-colors"
              style={{
                background: severity === s ? 'var(--color-accent)' : 'var(--color-bg)',
                color: severity === s ? '#fff' : 'var(--color-text-secondary)',
                border: `1px solid ${severity === s ? 'var(--color-accent)' : 'var(--color-border)'}`,
              }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Provider pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {PROVIDERS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setProvider(p)}
              className="h-6 px-2.5 rounded-full text-[11px] font-medium transition-colors"
              style={{
                background: provider === p ? 'var(--color-accent-secondary, #7c3aed)' : 'var(--color-bg)',
                color: provider === p ? '#fff' : 'var(--color-text-secondary)',
                border: `1px solid ${provider === p ? '#7c3aed' : 'var(--color-border)'}`,
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Queue rows */}
      <div className="space-y-3">
        {filtered.map((incident) => (
          <QueueRow
            key={incident.id}
            incident={incident}
            onApprove={() =>
              setVisible((current) => current.filter((item) => item.id !== incident.id))
            }
          />
        ))}
      </div>

      {filtered.length === 0 && (
        <div
          className="rounded-[12px] p-8 text-center text-[13px]"
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text-muted)',
          }}
        >
          {visible.length === 0
            ? 'No guardrails are awaiting approval.'
            : 'No incidents match the current filters.'}
        </div>
      )}
    </section>
  );
}
