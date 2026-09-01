'use client';

import { Box, Cloud, Server, Zap } from 'lucide-react';
import type { CloudProvider } from '@/lib/types';

const PROVIDERS: Array<{ value: CloudProvider; label: string; icon: typeof Cloud }> = [
  { value: 'AWS',     label: 'Amazon Web Services', icon: Cloud  },
  { value: 'GCP',     label: 'Google Cloud',         icon: Server },
  { value: 'Azure',   label: 'Microsoft Azure',      icon: Box    },
  { value: 'Generic', label: 'Generic / Other',      icon: Zap    },
];

export function ProviderSelector({
  value,
  onChange,
}: {
  value: CloudProvider;
  onChange: (value: CloudProvider) => void;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {PROVIDERS.map(({ value: provider, label, icon: Icon }) => {
        const selected = value === provider;
        return (
          <button
            key={provider}
            type="button"
            onClick={() => onChange(provider)}
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
              <Icon
                size={14}
                strokeWidth={1.75}
                style={{ color: selected ? 'var(--color-accent)' : 'var(--color-text-secondary)' }}
              />
              <span
                className="text-[13px] font-medium"
                style={{ color: selected ? 'var(--color-accent)' : 'var(--color-text-primary)' }}
              >
                {provider}
              </span>
            </div>
            <p className="text-[12px]" style={{ color: 'var(--color-text-muted)' }}>
              {label}
            </p>
          </button>
        );
      })}
    </div>
  );
}
