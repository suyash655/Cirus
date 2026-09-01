'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Plus } from 'lucide-react';
import { useArtifacts, useIncident, useIncidents } from '@/lib/hooks/use-incidents';
import { useWorkflowRunByIncident } from '@/lib/hooks/use-workflow';
import { IncidentSidebarList } from '@/components/workflow/IncidentSidebarList';
import { PipelineHeader } from '@/components/workflow/PipelineHeader';
import { PipelineStepper } from '@/components/workflow/PipelineStepper';
import { CardSkeleton } from '@/components/dashboard/CardSkeleton';

export default function WorkflowPage() {
  const { data: incidents = [], isLoading: loadingIncidents } = useIncidents();
  const [selectedId, setSelectedId] = useState<string>();
  const sortedIncidents = [...incidents].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  useEffect(() => { if (!selectedId && sortedIncidents[0]) setSelectedId(sortedIncidents[0].id); }, [selectedId, sortedIncidents]);
  const selected = sortedIncidents.find((incident) => incident.id === selectedId);
  const { data: incidentDetail } = useIncident(selectedId ?? '');
  const { data: run, isLoading: loadingRun } = useWorkflowRunByIncident(selectedId ?? '');
  const { data: artifacts = {} } = useArtifacts(selectedId ?? '');

  if (loadingIncidents) return <div className="min-h-screen bg-[var(--color-bg)] flex"><div className="w-[280px] border-r border-[var(--color-border)]" /><main className="flex-1 max-w-[720px] mx-auto px-8 py-10"><CardSkeleton /></main></div>;
  if (sortedIncidents.length === 0) return <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center"><div className="text-center"><h1 className="text-xl font-semibold text-[var(--color-text-primary)]">No incidents yet</h1><p className="text-sm text-[var(--color-text-secondary)] mt-2">Create one to see its pipeline.</p><Link href="/incidents/new" className="inline-flex items-center gap-2 mt-5 h-10 rounded-[var(--radius-md)] bg-[var(--color-accent)] px-4 text-sm text-white"><Plus size={16} /> Create incident</Link></div></div>;
  if (!selected) return null;

  return <div className="min-h-screen bg-[var(--color-bg)] flex"><IncidentSidebarList incidents={sortedIncidents} selectedId={selected.id} onSelect={(incident) => setSelectedId(incident.id)} /><main className="flex-1 max-w-[720px] mx-auto px-8 py-10"><PipelineHeader incident={selected} run={run} />{loadingRun ? <CardSkeleton /> : <PipelineStepper incident={{ ...selected, ...(incidentDetail ?? {}) }} run={run ?? null} artifacts={artifacts} />}</main></div>;
}
