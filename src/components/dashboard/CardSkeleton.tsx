export function CardSkeleton() {
  return (
    <div
      className="rounded-[12px] animate-pulse"
      style={{
        height: 140,
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
      }}
    />
  );
}

export function ChartSkeleton() {
  return (
    <div
      className="rounded-[12px] animate-pulse"
      style={{
        height: 240,
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
      }}
    />
  );
}
