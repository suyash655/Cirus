'use client';

import type { Incident } from '@/lib/types';
import { IncidentSidebarItem } from './IncidentSidebarItem';

export function IncidentSidebarList({ incidents, selectedId, onSelect }: { incidents: Incident[]; selectedId?: string; onSelect: (incident: Incident) => void }) {
  const sorted = [...incidents].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  return <aside className="w-[280px] shrink-0 border-r border-[var(--color-border)] min-h-screen sticky top-0 overflow-y-auto bg-[var(--color-surface)]"><div className="h-16 px-5 flex items-center border-b border-[var(--color-border)]"><div><p className="text-sm font-semibold text-[var(--color-text-primary)]">Workflow runs</p><p className="text-xs text-[var(--color-text-secondary)]">{sorted.length} incidents</p></div></div><div className="py-2">{sorted.map((incident) => <IncidentSidebarItem key={incident.id} incident={incident} isActive={incident.id === selectedId} onClick={() => onSelect(incident)} />)}</div></aside>;
}
