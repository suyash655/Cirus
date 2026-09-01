'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import type { ArtifactSet, Incident, WorkflowStage } from '@/lib/types';
import { NodeStatusIcon } from './NodeStatusIcon';
import { StageDetail } from './StageDetail';

export type VisualStage = { name: string; backendIds: string[] };

export function PipelineNode({ stage, backendStage, status, isLast, incident, artifacts }: { stage: VisualStage; backendStage?: WorkflowStage; status: 'complete' | 'active' | 'pending'; isLast: boolean; incident: Incident; artifacts: ArtifactSet }) {
  const [expanded, setExpanded] = useState(status === 'active');
  const canExpand = status !== 'pending';
  return <div className="relative pl-14 pb-8 last:pb-0">{!isLast && <div className="absolute left-[19px] top-10 bottom-0 w-[2px] transition-colors duration-500" style={{ background: status === 'complete' ? 'var(--color-accent)' : 'var(--color-border)' }} />}<div className="absolute left-0 top-0"><NodeStatusIcon status={status} /></div><button type="button" disabled={!canExpand} onClick={() => canExpand && setExpanded((open) => !open)} className="w-full flex items-center justify-between text-left disabled:cursor-default"><div><div className="text-sm font-medium text-[var(--color-text-primary)]">{stage.name}</div>{backendStage?.durationMs !== undefined && <div className="text-xs text-[var(--color-text-secondary)] mt-0.5">{backendStage.durationMs}ms</div>}</div>{canExpand && <ChevronDown size={16} strokeWidth={1.75} className={`text-[var(--color-text-tertiary)] transition-transform duration-150 ${expanded ? 'rotate-180' : ''}`} />}</button><AnimatePresence initial={false}>{expanded && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }} className="overflow-hidden"><div className="mt-3"><StageDetail name={stage.name} incident={incident} stage={backendStage} artifacts={artifacts} /></div></motion.div>}</AnimatePresence></div>;
}
