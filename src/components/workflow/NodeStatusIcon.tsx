'use client';

import { motion } from 'framer-motion';

export function NodeStatusIcon({ status }: { status: 'complete' | 'active' | 'pending' }) {
  if (status === 'complete') {
    return (
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center"
        style={{ background: 'var(--color-success-bg)' }}
      >
        <motion.svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <motion.path
            d="M3 8.5l3 3 7-7"
            stroke="var(--color-success)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          />
        </motion.svg>
      </div>
    );
  }

  if (status === 'active') {
    return (
      <div
        className="w-10 h-10 rounded-full border-2 flex items-center justify-center"
        style={{ borderColor: 'var(--color-accent)', background: 'var(--color-accent-bg)' }}
      >
        <div
          className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: 'var(--color-accent)', borderTopColor: 'transparent' }}
        />
      </div>
    );
  }

  return (
    <div
      className="w-10 h-10 rounded-full border-2"
      style={{
        borderColor: 'var(--color-border)',
        background: 'var(--color-surface)',
      }}
    />
  );
}
