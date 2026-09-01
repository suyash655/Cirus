'use client';

import { motion } from 'framer-motion';
import type { ArtifactSet, Incident, WorkflowRun } from '@/lib/types';
import { PipelineNode, type VisualStage } from './PipelineNode';
import { PipelineCompleteIllustration } from '@/components/illustrations/PipelineCompleteIllustration';

// Single source of truth stage definitions — matching shared/PipelineStepper names
const stages: VisualStage[] = [
  { name: 'Normalize',   backendIds: ['human-input', 'normalization'] },
  { name: 'Root cause',  backendIds: ['root-cause-classification'] },
  { name: 'Enrich',      backendIds: ['context-enrichment'] },
  { name: 'Generate',    backendIds: ['artifact-generation'] },
  { name: 'Validate',    backendIds: ['validator-critic'] },
  { name: 'Risk score',  backendIds: ['risk-scoring'] },
  { name: 'Citations',   backendIds: ['citation-extraction'] },
];

export function PipelineStepper({
  incident,
  run,
  artifacts,
}: {
  incident: Incident;
  run: WorkflowRun | null;
  artifacts: ArtifactSet;
}) {
  const backendStages = run?.stages ?? [];
  const activeIndex =
    run?.status === 'completed'
      ? stages.length - 1
      : stages.findIndex((s) => s.backendIds.includes(run?.currentStage ?? ''));

  return (
    <div aria-label="Incident pipeline">
      {stages.map((stage, index) => {
        const backendStage = backendStages.find((item) =>
          stage.backendIds.includes(item.id),
        );
        const status =
          run?.status === 'completed' || index < activeIndex
            ? 'complete'
            : index === activeIndex
              ? 'active'
              : 'pending';

        return (
          <PipelineNode
            key={stage.name}
            stage={stage}
            backendStage={backendStage}
            status={status}
            isLast={index === stages.length - 1}
            incident={incident}
            artifacts={artifacts}
          />
        );
      })}

      {run?.status === 'completed' && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="pt-6 flex justify-center"
        >
          <PipelineCompleteIllustration className="w-24 h-18" />
        </motion.div>
      )}
    </div>
  );
}
