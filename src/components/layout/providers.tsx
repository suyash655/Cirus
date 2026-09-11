'use client';

import * as React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useToasts } from '@/lib/store';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, XCircle, Info, AlertTriangle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Query Client ─────────────────────────────────────────────────────────────
// Instantiated inside a ref so each render tree (including SSR) gets its own
// isolated client — prevents request data from leaking across users in Next.js.
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

// ─── Toast UI ─────────────────────────────────────────────────────────────────
const toastIcons = {
  success: <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />,
  error: <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />,
  info: <Info className="w-4 h-4 text-sky-400 flex-shrink-0" />,
  warning: <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0" />,
};

const toastBorder = {
  success: 'border-emerald-500/20',
  error: 'border-red-500/20',
  info: 'border-sky-500/20',
  warning: 'border-amber-500/20',
};

function ToastContainer() {
  const { toasts, remove } = useToasts();

  return (
    <div
      className="fixed bottom-6 right-6 z-[100] flex flex-col gap-2 w-[360px] max-w-[calc(100vw-3rem)]"
      aria-live="polite"
      aria-label="Notifications"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, x: 40, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 40, scale: 0.95 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className={cn(
              'flex items-start gap-3 px-4 py-3 rounded-xl',
              'bg-surface border shadow-panel glass',
              toastBorder[toast.type],
            )}
            role="alert"
          >
            {toastIcons[toast.type]}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary">{toast.title}</p>
              {toast.description && (
                <p className="text-xs text-text-muted mt-0.5 leading-relaxed">
                  {toast.description}
                </p>
              )}
            </div>
            <button
              onClick={() => remove(toast.id)}
              className="flex-shrink-0 text-text-muted hover:text-text-primary transition-colors"
              aria-label="Dismiss notification"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// ─── Root Providers ───────────────────────────────────────────────────────────
function Providers({ children }: { children: React.ReactNode }) {
  const queryClientRef = React.useRef<QueryClient | null>(null);
  if (!queryClientRef.current) {
    queryClientRef.current = makeQueryClient();
  }

  return (
    <QueryClientProvider client={queryClientRef.current}>
      {children}
      <ToastContainer />
    </QueryClientProvider>
  );
}

export { Providers };
