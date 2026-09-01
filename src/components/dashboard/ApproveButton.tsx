'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, Loader2 } from 'lucide-react';

export function ApproveButton({ onApprove }: { onApprove: () => Promise<void> }) {
  const [state, setState] = useState<'idle' | 'approving' | 'done'>('idle');
  async function handleClick() {
    setState('approving');
    await onApprove();
    setState('done');
    window.setTimeout(() => setState('idle'), 900);
  }
  return <button type="button" disabled={state !== 'idle'} onClick={handleClick} className="relative inline-flex items-center justify-center min-w-[86px] h-9 bg-[var(--color-accent)] text-white rounded-[var(--radius-sm)] px-4 text-sm font-medium transition-transform duration-150 active:scale-95 disabled:opacity-80">
    <AnimatePresence mode="wait" initial={false}>
      {state === 'idle' && <motion.span key="label" exit={{ opacity: 0 }}>Approve</motion.span>}
      {state === 'approving' && <motion.span key="spin"><Loader2 className="animate-spin" size={16} /></motion.span>}
      {state === 'done' && <motion.span key="check" initial={{ scale: 0 }} animate={{ scale: 1 }}><Check size={16} /></motion.span>}
    </AnimatePresence>
  </button>;
}
