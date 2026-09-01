'use client';

import { useParams, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWorkflowRun } from '@/lib/hooks/use-workflow';
import { PageHeader } from '@/components/shared/page-header';
import { LoadingSpinner } from '@/components/shared/loading-spinner';
import { ErrorState } from '@/components/shared/error-state';
import { Dialog } from '@/components/ui/dialog';
import { CodeBlock } from '@/components/ui/code-block';
import { formatRelativeTime } from '@/lib/utils';
import { CheckCircle, AlertTriangle, Loader2, ArrowLeft, Clock, Zap } from 'lucide-react';
import Link from 'next/link';
import type { WorkflowRun, WorkflowStage } from '@/lib/types';

// The 8 stages requested by prompt
const VISUAL_STAGES = [
  { id: 'input', label: 'Human Input', icon: '📋', desc: 'Incident report ingestion' },
  { id: 'norm', label: 'Normalizer', icon: '⚡', desc: 'Structure extraction' },
  { id: 'rca', label: 'Root Cause Classifier', icon: '🔍', desc: 'Identify failure mechanism' },
  { id: 'context', label: 'Context Enrichment', icon: '🧠', desc: 'RAG on cloud docs' },
  { id: 'gen', label: 'Prevention Generator', icon: '🛡️', desc: 'Create code artifacts' },
  { id: 'critic', label: 'Validator / Critic', icon: '✅', desc: 'Syntax & hallucination check' },
  { id: 'approve', label: 'Human Approval', icon: '👤', desc: 'Manual review gate' },
  { id: 'pack', label: 'Output Pack', icon: '📦', desc: 'Exportable artifact bundle' },
];

function mapRunStatusToStageIndex(run: WorkflowRun): number {
  if (run.status === 'completed') return 8; // All done
  if (run.status === 'failed') return -1;
  // Map internal stages to visual index
  const stageMap: Record<string, number> = {
    'input': 0,
    'normalization': 1, 'normalizing': 1,
    'root-cause-classification': 2, 'classifying': 2,
    'context-enrichment': 3, 'enriching': 3,
    'artifact-generation': 4, 'generating': 4,
    'validator-critic': 5, 'validating': 5,
    'review': 6,
    'risk-scoring': 7, 'citation-extraction': 7, 'export': 7,
  };
  return run.currentStage ? (stageMap[run.currentStage] ?? 0) : 0;
}

export default function WorkflowVisualizerPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();
  const { data: run, isLoading, isError, refetch } = useWorkflowRun(id);
  
  const [selectedStage, setSelectedStage] = useState<typeof VISUAL_STAGES[0] | null>(null);

  if (isLoading) return <div className="p-20 flex justify-center"><LoadingSpinner size="lg" /></div>;
  if (isError || !run) return <ErrorState title="Workflow not found" retry={refetch} />;

  const activeIndex = mapRunStatusToStageIndex(run);

  return (
    <div className="max-w-6xl mx-auto pb-20">
      <Link href={`/incidents/${run.incidentId}`} className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Incident
      </Link>
      
      <PageHeader
        title="Pipeline Visualizer"
        description={`Workflow run for incident: ${run.incidentId}`}
        badge={
          <span className="text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 border rounded bg-bg-surface text-text-primary border-border-strong">
            {run.status === 'running' ? <><Loader2 className="w-3 h-3 animate-spin mr-1 inline" /> RUNNING</> : 
             run.status === 'completed' ? <><CheckCircle className="w-3 h-3 mr-1 inline" /> COMPLETED</> : 
             run.status}
          </span>
        }
      />

      <div className="grid lg:grid-cols-[1fr_380px] gap-8 mt-12">
        {/* Node Graph */}
        <div className="relative">
          {/* Connector Line Background */}
          <div className="absolute left-[39px] top-8 bottom-8 w-1 bg-border-dim rounded-full" />
          
          {/* Active Connector Progress */}
          <motion.div 
            className="absolute left-[39px] top-8 w-1 bg-text-primary rounded-full"
            initial={{ height: 0 }}
            animate={{ height: `${Math.max(0, Math.min(100, (activeIndex / (VISUAL_STAGES.length - 1)) * 100))}%` }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />

          <div className="flex flex-col gap-10 relative">
            {VISUAL_STAGES.map((stage, i) => {
              const isActive = i === activeIndex;
              const isDone = i < activeIndex;
              const isPending = i > activeIndex;

              return (
                <motion.div 
                  key={stage.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex items-center gap-6 group cursor-pointer"
                  onClick={() => setSelectedStage(stage)}
                >
                  {/* Node */}
                  <div className="relative">
                    {isActive && (
                      <span className="absolute inset-0 rounded-full bg-text-primary opacity-20 animate-ping scale-150" />
                    )}
                    <div 
                      className="relative w-20 h-20 rounded-2xl flex items-center justify-center text-3xl z-10 transition-all duration-300"
                      style={{
                        background: isDone ? 'hsl(var(--bg-raised))' : isActive ? 'hsl(var(--bg-surface))' : 'hsl(var(--bg-base))',
                        border: `2px solid ${isDone ? 'hsl(var(--text-primary))' : isActive ? 'hsl(var(--text-primary))' : 'hsl(var(--border-base))'}`,
                        filter: isPending ? 'grayscale(100%) opacity(40%)' : 'none'
                      }}
                    >
                      {isDone && !isActive && (
                        <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-text-primary text-bg-base flex items-center justify-center border-2 border-bg-base">
                          <CheckCircle className="w-4 h-4" />
                        </div>
                      )}
                      {stage.icon}
                    </div>
                  </div>

                  {/* Label */}
                  <div className="flex-1 p-4 rounded-xl transition-all duration-200 group-hover:bg-bg-raised border border-transparent group-hover:border-border-dim">
                    <h3 className={`text-lg font-bold ${isActive ? 'text-text-primary' : isDone ? 'text-text-secondary' : 'text-text-muted'}`}>
                      {stage.label}
                    </h3>
                    <p className="text-sm text-text-muted mt-1">{stage.desc}</p>
                    {isActive && (
                      <div className="flex items-center gap-2 mt-3">
                        <span className="text-[10px] font-bold text-text-primary bg-bg-surface px-2 py-0.5 rounded border border-border-strong uppercase tracking-widest">
                          Processing
                        </span>
                        <span className="text-xs text-text-faint">{formatRelativeTime(run.updatedAt)}</span>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Active Stage Side Panel */}
        <div className="relative">
          <div className="sticky top-24">
            <AnimatePresence mode="wait">
              {selectedStage ? (
                <motion.div
                  key={selectedStage.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="rounded-2xl p-6 glass-heavy border border-border-strong shadow-panel"
                >
                  <div className="flex items-center gap-4 mb-6 pb-6 border-b border-border-dim">
                    <div className="w-12 h-12 rounded-xl bg-bg-raised flex items-center justify-center text-2xl border border-border-base">
                      {selectedStage.icon}
                    </div>
                    <div>
                      <h4 className="text-lg font-bold text-text-primary">{selectedStage.label}</h4>
                      <p className="text-xs text-text-muted font-mono uppercase tracking-wider">{selectedStage.id}</p>
                    </div>
                  </div>

                  <div className="flex flex-col gap-6">
                    <div>
                      <span className="text-xs font-semibold text-text-muted uppercase tracking-wider block mb-2">Description</span>
                      <p className="text-sm text-text-secondary leading-relaxed">{selectedStage.desc}</p>
                    </div>
                    
                    <div className="p-4 rounded-xl bg-bg-surface border border-border-base">
                      <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest block mb-3">Model Used</span>
                      <div className="flex items-center gap-2 text-sm text-text-primary font-medium">
                        <Zap className="w-4 h-4 text-text-muted" />
                        {selectedStage.id === 'input' || selectedStage.id === 'approve' || selectedStage.id === 'pack'
                          ? 'Deterministic System'
                          : run.stages.find(s => s.id === selectedStage.id)?.modelId ||
                            run.stages.find(s => s.id === selectedStage.id)?.output?.modelId ||
                            run.modelId ||
                            'Unknown Model'}
                      </div>
                    </div>

                    {selectedStage.id !== 'input' && selectedStage.id !== 'approve' && selectedStage.id !== 'pack' && (
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-4 rounded-xl bg-bg-surface border border-border-base col-span-2">
                          <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest block mb-2">Stage Output Summary</span>
                          <p className="text-xs text-text-secondary leading-relaxed font-mono">
                            {run.stages.find(s => s.id === selectedStage.id)?.output
                              ? JSON.stringify(run.stages.find(s => s.id === selectedStage.id)?.output, null, 2).slice(0, 300) + '...'
                              : 'Waiting for output...'}
                          </p>
                        </div>
                      </div>
                    )}

                    {run.stages.find(s => s.id === selectedStage.id)?.confidence !== undefined && (
                      <div className="p-4 rounded-xl bg-bg-raised border border-border-strong">
                        <span className="text-[10px] font-bold text-text-primary uppercase tracking-widest block mb-2">Confidence Score</span>
                        <div className="flex items-end gap-2">
                          <span className="text-2xl font-bold text-text-primary leading-none">
                            {Math.round(run.stages.find(s => s.id === selectedStage.id)!.confidence! * 100)}%
                          </span>
                        </div>
                      </div>
                    )}

                    {run.stages.find(s => s.id === selectedStage.id)?.logs && (
                      <div>
                        <span className="text-[10px] font-bold text-text-muted uppercase tracking-widest block mb-2">Execution Logs</span>
                        <CodeBlock 
                          code={run.stages.find(s => s.id === selectedStage.id)?.logs?.join('\n') || 'No logs available'} 
                          language="text" 
                          showLineNumbers={false} 
                        />
                      </div>
                    )}
                  </div>
                </motion.div>
              ) : (
                <div className="rounded-2xl p-10 border border-dashed border-border-base flex flex-col items-center justify-center text-center opacity-60">
                  <span className="text-4xl mb-4">👆</span>
                  <p className="text-sm font-medium text-text-secondary">Select a pipeline stage<br/>to view details and logs.</p>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
