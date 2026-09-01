'use client';

import { useUIStore } from '@/lib/store';
import { Sidebar } from '@/components/layout/sidebar';
import { TopNav } from '@/components/layout/top-nav';
import { motion } from 'framer-motion';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);

  return (
    <div className="flex min-h-screen" style={{ background: 'var(--color-bg)' }}>
      <Sidebar />
      <motion.div
        animate={{ marginLeft: collapsed ? 64 : 240 }}
        transition={{ duration: 0.25, ease: 'easeInOut' }}
        className="flex-1 flex flex-col min-h-screen min-w-0"
      >
        <TopNav />
        <main className="flex-1 mt-14 min-w-0" style={{ padding: '32px 24px' }}>
          {children}
        </main>
      </motion.div>
    </div>
  );
}
