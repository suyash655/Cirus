'use client';

import { AlertTriangle, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface ErrorStateProps {
  title?: string;
  message?: string;
  retry?: () => void;
  className?: string;
  compact?: boolean;
}

function ErrorState({
  title = 'Something went wrong',
  message,
  retry,
  className,
  compact = false,
}: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex flex-col items-center justify-center text-center',
        compact ? 'gap-3 py-8 px-6' : 'gap-4 py-16 px-8',
        className,
      )}
    >
      <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-red-500/10 border border-red-500/20">
        <AlertTriangle className="w-6 h-6 text-red-400" />
      </div>
      <div className="flex flex-col gap-1.5 max-w-sm">
        <h3 className="text-base font-semibold text-text-primary">{title}</h3>
        {message && <p className="text-sm text-text-muted">{message}</p>}
      </div>
      {retry && (
        <Button variant="outline" size="sm" onClick={retry}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Try again
        </Button>
      )}
    </motion.div>
  );
}

export { ErrorState };
