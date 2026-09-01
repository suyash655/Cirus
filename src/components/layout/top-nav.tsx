'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bell, ChevronRight, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/lib/store';

function buildBreadcrumbs(pathname: string) {
  const segments = pathname.split('/').filter(Boolean);
  const crumbs: { label: string; href: string }[] = [];
  const labelMap: Record<string, string> = {
    dashboard: 'Incidents',
    incidents: 'Incidents',
    new: 'New Incident',
    workflow: 'Artifacts',
    analytics: 'Analytics',
    settings: 'Settings',
  };
  let path = '';
  for (const seg of segments) {
    path += `/${seg}`;
    crumbs.push({ label: labelMap[seg] ?? seg, href: path });
  }
  return crumbs;
}

function TopNav() {
  const { collapsed } = useSidebar();
  const pathname = usePathname();
  const crumbs = buildBreadcrumbs(pathname);

  return (
    <header
      className="fixed top-0 right-0 z-20 flex items-center justify-between h-14 px-6"
      style={{
        left: collapsed ? 64 : 240,
        borderBottom: '1px solid var(--color-border)',
        background: 'rgba(250,250,248,0.92)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        transition: 'left 0.25s ease',
      }}
    >
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 min-w-0 flex-1">
        {crumbs.map((crumb, i) => (
          <span key={crumb.href} className="flex items-center gap-1.5 min-w-0">
            {i > 0 && (
              <ChevronRight
                className="h-3.5 w-3.5 flex-shrink-0"
                style={{ color: 'var(--color-text-muted)' }}
              />
            )}
            {i === crumbs.length - 1 ? (
              <span
                className="text-[13px] font-medium truncate"
                style={{ color: 'var(--color-text-primary)' }}
              >
                {crumb.label}
              </span>
            ) : (
              <Link
                href={crumb.href}
                className="text-[13px] truncate transition-colors"
                style={{ color: 'var(--color-text-muted)' }}
              >
                {crumb.label}
              </Link>
            )}
          </span>
        ))}
      </nav>

      {/* Right actions */}
      <div className="flex items-center gap-3">
        {/* Notification bell */}
        <button
          className="p-1.5 rounded-md transition-colors relative"
          style={{ color: 'var(--color-text-muted)' }}
          id="topnav-notifications"
          aria-label="Notifications"
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-text-muted)')}
        >
          <Bell className="w-4 h-4" />
          <span
            className="absolute top-1 right-1.5 w-1.5 h-1.5 rounded-full"
            style={{ background: 'var(--color-accent)' }}
          />
        </button>

        {/* Primary CTA — THE ONE ACCENT ELEMENT on this bar */}
        <Link href="/incidents/new" id="topnav-new-incident">
          <button className="c-btn-primary text-[13px] h-8 px-3 gap-1.5">
            <Plus className="w-3.5 h-3.5" />
            Declare incident
          </button>
        </Link>

        {/* Avatar */}
        <div
          className="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer transition-colors"
          style={{
            background: 'var(--color-bg)',
            border: '1px solid var(--color-border-strong)',
            color: 'var(--color-text-secondary)',
          }}
          id="topnav-avatar"
          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.borderColor = 'var(--color-text-primary)')}
          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.borderColor = 'var(--color-border-strong)')}
        >
          <span className="text-[10px] font-medium">SR</span>
        </div>
      </div>
    </header>
  );
}

export { TopNav };
