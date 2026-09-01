'use client';

import type { Severity } from '@/lib/types';

const SEVERITIES: Array<{
  value: Severity;
  label: string;
  description: string;
  dotColor: string;
}> = [
  { value: 'P1', label: 'P1 — Critical',   description: 'Production down or major data exposure', dotColor: 'var(--color-danger)' },
  { value: 'P2', label: 'P2 — High',        description: 'Significant impact, degraded service',  dotColor: 'var(--color-warning)' },
  { value: 'P3', label: 'P3 — Medium',      description: 'Partial impact, workaround available',  dotColor: 'var(--color-accent)' },
  { value: 'P4', label: 'P4 — Low',         description: 'Minor issue, minimal user impact',       dotColor: 'var(--color-success)' },
];

export function SeveritySelector({
  value,
  onChange,
}: {
  value: Severity;
  onChange: (value: Severity) => void;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {SEVERITIES.map((sev) => {
        const selected = value === sev.value;
        return (
          <button
            key={sev.value}
            type="button"
            onClick={() => onChange(sev.value)}
            className="p-4 rounded-[8px] border text-left cursor-pointer transition-all duration-150"
            style={{
              background: selected ? 'var(--color-accent-bg)' : 'var(--color-surface)',
              borderColor: selected ? 'var(--color-accent)' : 'var(--color-border)',
            }}
            onMouseEnter={(e) => {
              if (!selected) (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-border-strong)';
            }}
            onMouseLeave={(e) => {
              if (!selected) (e.currentTarget as HTMLElement).style.borderColor = 'var(--color-border)';
            }}
          >
            <div className="flex items-center gap-2 mb-1">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: sev.dotColor }}
              />
              <span
                className="text-[13px] font-medium"
                style={{ color: 'var(--color-text-primary)' }}
              >
                {sev.label}
              </span>
            </div>
            <p className="text-[12px]" style={{ color: 'var(--color-text-secondary)' }}>
              {sev.description}
            </p>
          </button>
        );
      })}
    </div>
  );
}
