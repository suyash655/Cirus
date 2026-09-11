'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cirusAPI } from '@/lib/api';
import { useToasts } from '@/lib/store';

// ─── Incidents list ───────────────────────────────────────────────────────────
export function useIncidents() {
  return useQuery({
    queryKey: ['incidents'],
    queryFn: () => cirusAPI.getIncidents(),
    staleTime: 30_000,
    refetchInterval: (query) => {
      // Poll every 3s if any incident is still processing
      const data = query.state.data;
      const hasProcessing = data?.some((i) => i.status === 'processing');
      return hasProcessing ? 3000 : false;
    },
  });
}

// ─── Single incident detail ───────────────────────────────────────────────────
export function useIncident(id: string) {
  return useQuery({
    queryKey: ['incident', id],
    queryFn: () => cirusAPI.getIncident(id),
    staleTime: 5_000,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'processing' ? 2000 : false;
    },
    enabled: Boolean(id),
  });
}

// ─── Artifacts for incident ───────────────────────────────────────────────────
export function useArtifacts(incidentId: string) {
  return useQuery({
    queryKey: ['artifacts', incidentId],
    queryFn: () => cirusAPI.getArtifacts(incidentId),
    staleTime: 60_000,
    enabled: Boolean(incidentId),
  });
}

// ─── Risk score ───────────────────────────────────────────────────────────────
export function useRiskScore(incidentId: string) {
  return useQuery({
    queryKey: ['risk', incidentId],
    queryFn: () => cirusAPI.getRiskScore(incidentId),
    staleTime: 120_000,
    enabled: Boolean(incidentId),
  });
}

// ─── Extraction result ────────────────────────────────────────────────────────
export function useExtraction(incidentId: string) {
  return useQuery({
    queryKey: ['extraction', incidentId],
    queryFn: () => cirusAPI.getExtraction(incidentId),
    staleTime: 120_000,
    enabled: Boolean(incidentId),
  });
}

// ─── Create incident ──────────────────────────────────────────────────────────
export function useCreateIncident() {
  const queryClient = useQueryClient();
  const { add: addToast } = useToasts();

  return useMutation({
    mutationFn: cirusAPI.createIncident,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      addToast({
        type: 'success',
        title: 'Incident submitted',
        description: 'AI pipeline started — artifacts will be ready in ~30 seconds.',
      });
    },
    onError: (error: Error) => {
      addToast({
        type: 'error',
        title: 'Submission failed',
        description: error.message,
      });
    },
  });
}

// ─── Delete incident ──────────────────────────────────────────────────────────
export function useDeleteIncident() {
  const queryClient = useQueryClient();
  const { add: addToast } = useToasts();

  return useMutation({
    mutationFn: (id: string) => cirusAPI.deleteIncident(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      addToast({ type: 'info', title: 'Incident deleted' });
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Delete failed', description: error.message });
    },
  });
}

// ─── Regenerate single artifact ───────────────────────────────────────────────
export function useRegenerateArtifact(incidentId: string) {
  const queryClient = useQueryClient();
  const { add: addToast } = useToasts();

  return useMutation({
    mutationFn: (type: Parameters<typeof cirusAPI.regenerateArtifact>[1]) =>
      cirusAPI.regenerateArtifact(incidentId, type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts', incidentId] });
      addToast({ type: 'success', title: 'Artifact regenerated' });
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'Regeneration failed', description: error.message });
    },
  });
}

// ─── Dashboard stats ──────────────────────────────────────────────────────────
export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => cirusAPI.getDashboardStats(),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

// ─── Create GitOps Pull Request ───────────────────────────────────────────────
export function useCreateGitOpsPR() {
  const queryClient = useQueryClient();
  const { add: addToast } = useToasts();

  return useMutation({
    mutationFn: (payload: Parameters<typeof cirusAPI.createGitOpsPR>[0]) =>
      cirusAPI.createGitOpsPR(payload),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      addToast({
        type: 'success',
        title: `PR #${data.prNumber} created`,
        description: `Branch: ${data.branchName} — ${data.filesCommitted.length} files committed.`,
      });
    },
    onError: (error: Error) => {
      addToast({ type: 'error', title: 'GitOps PR failed', description: error.message });
    },
  });
}

// ─── Incident compliance ──────────────────────────────────────────────────────
export function useIncidentCompliance(incidentId: string | undefined) {
  return useQuery({
    queryKey: ['compliance', incidentId],
    queryFn: () => cirusAPI.getIncidentCompliance(incidentId!),
    enabled: Boolean(incidentId),
    staleTime: 60_000,
  });
}
