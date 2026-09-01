'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  BarChart3,
  ChevronLeft,
  Settings,
  Shield,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/lib/store';
import { Tooltip } from '@/components/ui/tooltip';

// Nav items — "New Incident" is NOT a nav item, it's a top-bar CTA
const NAV_ITEMS = [
  { id: 'incidents',  label: 'Incidents',  icon: AlertTriangle, href: '/dashboard',      exact: false },
  { id: 'artifacts',  label: 'Artifacts',  icon: Shield,        href: '/workflow',        exact: false },
  { id: 'analytics',  label: 'Analytics',  icon: BarChart3,     href: '/analytics',       exact: false },
  { id: 'settings',   label: 'Settings',   icon: Settings,      href: '/settings',        exact: false },
];

function Sidebar() {
  const { collapsed, toggle } = useSidebar();
  const pathname = usePathname();

  const isActive = (href: string, exact: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
      className={cn(
        'fixed left-0 top-0 bottom-0 z-30 flex flex-col',
        'border-r bg-[var(--color-surface)] overflow-hidden',
      )}
      style={{ borderColor: 'var(--color-border)' }}
    >
      {/* Logo lockup */}
      <div
        className="flex items-center h-16 px-4 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--color-border)' }}
      >
        <Link href="/" className="flex items-center gap-3 min-w-0">
          <div
            className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--color-text-primary)' }}
          >
            <Zap className="w-4 h-4" style={{ color: '#FFFFFF' }} />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -8 }}
                transition={{ duration: 0.15 }}
                className="text-sm font-medium whitespace-nowrap tracking-tight"
                style={{ color: 'var(--color-text-primary)', letterSpacing: '0.05em' }}
              >
                CIRUS
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
      </div>

      {/* Environment badge */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mx-3 mt-3 mb-1 flex items-center gap-2 px-3 py-2 rounded-md"
            style={{
              background: 'var(--color-accent-bg)',
              border: '1px solid rgba(42,120,214,0.2)',
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--color-accent)' }} />
            <span className="text-[11px] font-medium uppercase tracking-widest" style={{ color: 'var(--color-accent)' }}>
              Production
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Nav */}
      <nav
        className="flex-1 py-3 px-2 flex flex-col gap-0.5 overflow-y-auto"
        aria-label="Main navigation"
      >
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href, item.exact);
          const Icon = item.icon;

          const linkContent = (
            <Link
              key={item.id}
              href={item.href}
              id={`nav-${item.id}`}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'relative flex items-center gap-3 px-3 py-2.5 rounded-lg',
                'transition-all duration-150 group min-w-0',
              )}
              style={{
                background: active ? 'var(--color-bg)' : 'transparent',
                border: active ? '1px solid var(--color-border-strong)' : '1px solid transparent',
                color: active ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = 'var(--color-bg)';
                  (e.currentTarget as HTMLElement).style.color = 'var(--color-text-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = 'transparent';
                  (e.currentTarget as HTMLElement).style.color = 'var(--color-text-muted)';
                }
              }}
            >
              {active && (
                <motion.span
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full"
                  style={{ background: 'var(--color-accent)' }}
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              <Icon
                className={cn('flex-shrink-0', collapsed ? 'mx-auto' : '')}
                style={{ width: 16, height: 16 }}
              />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.1 }}
                    className="text-sm font-medium whitespace-nowrap"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );

          return collapsed ? (
            <Tooltip key={item.id} content={item.label} side="right">
              {linkContent}
            </Tooltip>
          ) : (
            linkContent
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div
        className="p-2 flex-shrink-0"
        style={{ borderTop: '1px solid var(--color-border)' }}
      >
        <button
          onClick={toggle}
          id="sidebar-collapse-btn"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="flex items-center justify-center w-full py-2 rounded-lg transition-all duration-150"
          style={{ color: 'var(--color-text-muted)' }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLElement).style.background = 'var(--color-bg)';
            (e.currentTarget as HTMLElement).style.color = 'var(--color-text-primary)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLElement).style.background = 'transparent';
            (e.currentTarget as HTMLElement).style.color = 'var(--color-text-muted)';
          }}
        >
          <motion.div animate={{ rotate: collapsed ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronLeft className="w-4 h-4" />
          </motion.div>
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="ml-2 text-xs"
              >
                Collapse
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  );
}

export { Sidebar };
