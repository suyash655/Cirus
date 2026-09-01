'use client';

import { ArrowLeft, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import type { Incident, WorkflowRun } from '@/lib/types';

export function PipelineHeader({ incident, run }: { incident: Incident; run?: WorkflowRun | null }) {
  return <header className="mb-8"><Link href={`/incidents/${incident.id}`} className="inline-flex items-center gap-2 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] mb-6"><ArrowLeft size={14} strokeWidth={1.75} /> Back to incident</Link><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs uppercase tracking-[0.16em] text-[var(--color-accent)]">Pipeline visualizer</p><h1 className="text-2xl font-semibold text-[var(--color-text-primary)] mt-2">{incident.title}</h1><p className="text-sm text-[var(--color-text-secondary)] mt-1">{incident.id} · {incident.provider} · {incident.severity}</p></div>{run && <div className="flex items-center gap-2 rounded-[var(--radius-sm)] border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-text-secondary)]"><span className={`h-2 w-2 rounded-full ${run.status === 'completed' ? 'bg-[var(--color-accent)]' : run.status === 'failed' ? 'bg-[var(--color-danger)]' : 'bg-[var(--color-accent)] animate-pulse'}`} />{run.status}<Link href={`/workflow/${run.id}`} title="Open run detail" className="ml-1 text-[var(--color-text-tertiary)] hover:text-[var(--color-accent)]"><ExternalLink size={14} strokeWidth={1.75} /></Link></div>}</div></header>;
}
