'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon?: string; // emoji
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  compact?: boolean;
}

function EmptyState({
  icon = '✦',
  title,
  description,
  action,
  secondaryAction,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={cn(
        'flex flex-col items-center justify-center text-center',
        compact ? 'gap-3 py-10 px-6' : 'gap-5 py-20 px-8',
        className,
      )}
    >
      {/* Icon with glow */}
      <div className="relative">
        <div className="absolute inset-0 blur-2xl bg-rose-500/10 rounded-full scale-150" />
        <div
          className={cn(
            'relative flex items-center justify-center rounded-2xl',
            'border border-border bg-surface-raised',
            compact ? 'w-12 h-12 text-xl' : 'w-16 h-16 text-3xl',
          )}
        >
          {icon}
        </div>
      </div>

      <div className="flex flex-col gap-1.5 max-w-xs">
        <h3
          className={cn(
            'font-semibold text-text-primary',
            compact ? 'text-sm' : 'text-base',
          )}
        >
          {title}
        </h3>
        {description && (
          <p className="text-sm text-text-muted leading-relaxed">{description}</p>
        )}
      </div>

      {(action || secondaryAction) && (
        <div className="flex items-center gap-3 flex-wrap justify-center">
          {action && (
            <Button variant="default" size="sm" onClick={action.onClick}>
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button variant="ghost" size="sm" onClick={secondaryAction.onClick}>
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </motion.div>
  );
}

export { EmptyState };
