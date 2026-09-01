'use client';

import { useQuery } from '@tanstack/react-query';
import { cirusAPI } from '@/lib/api';

// ─── Workflow run by ID ───────────────────────────────────────────────────────
export function useWorkflowRun(runId: string) {
  return useQuery({
    queryKey: ['workflow', runId],
    queryFn: () => cirusAPI.getWorkflowRun(runId),
    staleTime: 5_000,
    // Poll every 2s if the run is still active
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'queued' ? 2000 : false;
    },
    enabled: Boolean(runId),
  });
}

// ─── Workflow run by incident ─────────────────────────────────────────────────
export function useWorkflowRunByIncident(incidentId: string) {
  return useQuery({
    queryKey: ['workflow-by-incident', incidentId],
    queryFn: () => cirusAPI.getWorkflowRunByIncident(incidentId),
    staleTime: 2_000,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'running' || status === 'queued' ? 1500 : false;
    },
    enabled: Boolean(incidentId),
  });
}
