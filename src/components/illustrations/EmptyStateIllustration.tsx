export function EmptyStateIllustration({ className = '' }: { className?: string }) {
  return <svg className={className} viewBox="0 0 64 64" fill="none" aria-hidden="true"><path d="M18 10h28a4 4 0 0 1 4 4v36H14V14a4 4 0 0 1 4-4Z" stroke="var(--color-text-secondary)" strokeWidth="2"/><path d="M23 22h18M23 30h18M23 38h10M39 47l4 4 8-9" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}
