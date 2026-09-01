'use client';

import type { LucideIcon } from 'lucide-react';
import { useCountUp } from '@/hooks/useCountUp';

export function StatCard({
  label,
  value,
  trend,
  icon: Icon,
  onClick,
  children,
}: {
  label: string;
  value?: number;
  trend?: number;
  icon: LucideIcon;
  onClick?: () => void;
  children?: React.ReactNode;
}) {
  const displayValue = useCountUp(value ?? 0);

  return (
    <div
      onClick={onClick}
      className={onClick ? 'c-card-interactive' : 'c-metric-tile'}
      style={{ minHeight: 140 }}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="c-metric-label">{label}</span>
        <Icon size={16} strokeWidth={1.75} style={{ color: 'var(--color-text-muted)' }} />
      </div>

      {children ?? (
        <p className="c-metric-value tabular-nums">{displayValue}</p>
      )}

      {trend !== undefined && !children && (
        <p className="c-metric-delta mt-1">
          {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% vs last period
        </p>
      )}
    </div>
  );
}
