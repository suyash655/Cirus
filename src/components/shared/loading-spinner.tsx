'use client';

import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  label?: string;
  className?: string;
  variant?: 'ring' | 'dots' | 'pulse';
}

const sizeMap = { sm: 16, md: 24, lg: 40, xl: 64 };

function LoadingSpinner({
  size = 'md',
  label,
  className,
  variant = 'ring',
}: LoadingSpinnerProps) {
  const px = sizeMap[size];

  if (variant === 'dots') {
    return (
      <div className={cn('flex items-center gap-1.5', className)}>
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-text-muted"
            animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1, 0.8] }}
            transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
          />
        ))}
        {label && <span className="text-sm text-text-muted ml-1">{label}</span>}
      </div>
    );
  }

  if (variant === 'pulse') {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <motion.div
          className="rounded-full bg-border-base"
          style={{ width: px, height: px }}
          animate={{ scale: [1, 1.3, 1], opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
        {label && <span className="text-sm text-text-muted">{label}</span>}
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col items-center gap-3', className)}>
      <svg
        width={px}
        height={px}
        viewBox="0 0 24 24"
        fill="none"
        className="animate-spin"
        aria-hidden="true"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="hsl(var(--border-base))"
          strokeWidth="2.5"
        />
        <path
          d="M12 2a10 10 0 0 1 10 10"
          stroke="hsl(var(--text-primary))"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
      {label && (
        <span className="text-sm text-text-muted">{label}</span>
      )}
    </div>
  );
}

// ─── Full-page loading overlay ────────────────────────────────────────────────
function PageLoader({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="fixed inset-0 z-40 flex flex-col items-center justify-center bg-bg-base/80 backdrop-blur-sm gap-4">
      <LoadingSpinner size="xl" />
      <p className="text-sm text-text-muted">{label}</p>
    </div>
  );
}

// ─── Inline skeleton block ────────────────────────────────────────────────────
function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'rounded-lg bg-border-dim animate-pulse',
        className,
      )}
    />
  );
}

export { LoadingSpinner, PageLoader, Skeleton };
