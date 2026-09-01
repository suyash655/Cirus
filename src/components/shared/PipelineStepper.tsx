'use client';

import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

// Single source of truth for pipeline stage names — used everywhere
export const PIPELINE_STAGES = [
  'Normalize',
  'Root cause',
  'Enrich',
  'Generate',
  'Validate',
  'Risk score',
  'Citations',
] as const;

export type PipelineStageStatus = 'done' | 'active' | 'pending';

interface PipelineStepperProps {
  /** Index of the currently active stage (0-based). -1 = none active yet. */
  currentIndex: number;
  /** compact: show dots only (no labels). full: show dots + labels */
  compact?: boolean;
  className?: string;
}

export function PipelineStepper({ currentIndex, compact = false, className }: PipelineStepperProps) {
  return (
    <div className={cn('flex items-center', compact ? 'gap-1' : 'gap-0', className)} role="list" aria-label="Pipeline stages">
      {PIPELINE_STAGES.map((stage, i) => {
        const isDone   = i < currentIndex;
        const isActive = i === currentIndex;

        return (
          <div key={stage} className="flex items-center" role="listitem">
            {/* Stage node */}
            <div
              className={cn(
                'flex items-center justify-center rounded-full transition-all duration-200',
                compact ? 'w-6 h-6' : 'w-8 h-8',
                isDone   && 'c-stage-done',
                isActive && 'c-stage-active',
                !isDone && !isActive && 'c-stage-pending',
              )}
              aria-label={`${stage}: ${isDone ? 'done' : isActive ? 'active' : 'pending'}`}
            >
              {isDone ? (
                <Check className={compact ? 'w-3 h-3' : 'w-4 h-4'} strokeWidth={2.5} />
              ) : (
                <span className={cn('font-medium', compact ? 'text-[9px]' : 'text-[10px]')}>
                  {isActive ? '●' : '○'}
                </span>
              )}
            </div>

            {/* Label (full mode only) */}
            {!compact && (
              <span
                className={cn(
                  'mx-2 text-[13px] font-normal transition-colors duration-200',
                  isDone   && 'text-[var(--color-text-muted)]',
                  isActive && 'text-[var(--color-accent)]',
                  !isDone && !isActive && 'text-[var(--color-text-muted)]',
                )}
              >
                {stage}
              </span>
            )}

            {/* Connector line */}
            {i < PIPELINE_STAGES.length - 1 && (
              <div
                className={cn(
                  'transition-colors duration-500',
                  compact ? 'w-3 h-px' : 'w-6 h-px',
                  isDone ? 'bg-[var(--color-success)]' : 'bg-[var(--color-border)]',
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
