'use client';

import { Circle } from 'lucide-react';
import type { Incident } from '@/lib/types';
import { formatRelativeTime } from '@/lib/utils';

export function IncidentSidebarItem({ incident, isActive, onClick }: { incident: Incident; isActive: boolean; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`w-full text-left px-4 py-3 border-l-2 transition-colors duration-150 ${isActive ? 'border-l-[var(--color-accent)] bg-[var(--color-accent-soft)]' : 'border-l-transparent hover:bg-[var(--color-border)]/30'}`}>
    <div className="text-sm font-medium text-[var(--color-text-primary)] truncate">{incident.title}</div>
    <div className="text-xs text-[var(--color-text-secondary)] mt-1 flex items-center gap-2"><Circle size={8} fill="currentColor" strokeWidth={1.75} className={incident.severity === 'P1' ? 'text-[var(--color-danger)]' : 'text-[var(--color-accent)]'} />{incident.severity}<span>·</span>{formatRelativeTime(incident.createdAt)}</div>
  </button>;
}
