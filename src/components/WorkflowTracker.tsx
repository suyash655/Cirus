'use client';

import { PipelineStepper, PIPELINE_STAGES } from '@/components/shared/PipelineStepper';
import { useWorkflowRunByIncident } from '@/lib/hooks/use-workflow';

// Map backend stage IDs to the shared pipeline stage index
function getStageIndex(currentStage: string | undefined, status: string | undefined): number {
  if (status === 'completed') return PIPELINE_STAGES.length;
  const map: Record<string, number> = {
    'human-input':              0,
    'normalization':            0,
    'root-cause-classification':1,
    'context-enrichment':       2,
    'artifact-generation':      3,
    'validator-critic':         4,
    'risk-scoring':             5,
    'citation-extraction':      6,
  };
  return map[currentStage ?? ''] ?? 0;
}

export function WorkflowTracker({ incidentId }: { incidentId: string }) {
  const { data: run } = useWorkflowRunByIncident(incidentId);
  const currentIndex = getStageIndex(run?.currentStage, run?.status);

  return (
    <div
      className="rounded-[12px] p-6 mb-6"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
      }}
    >
      <p
        className="text-[12px] font-medium mb-4 uppercase tracking-[0.1em]"
        style={{ color: 'var(--color-text-muted)' }}
      >
        Pipeline
      </p>
      <div className="overflow-x-auto">
        <PipelineStepper currentIndex={currentIndex} compact={false} />
      </div>
    </div>
  );
}
