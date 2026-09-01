import { cn } from '@/lib/utils';

function Separator({ className, orientation = 'horizontal' }: {
  className?: string;
  orientation?: 'horizontal' | 'vertical';
}) {
  return (
    <div
      role="separator"
      className={cn(
        'flex-shrink-0 bg-border',
        orientation === 'horizontal' ? 'h-px w-full' : 'w-px h-full',
        className,
      )}
    />
  );
}

export { Separator };
