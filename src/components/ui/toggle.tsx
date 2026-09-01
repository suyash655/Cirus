'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  id?: string;
  size?: 'sm' | 'md';
}

function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled,
  id,
  size = 'md',
}: ToggleProps) {
  const toggleId = id ?? `toggle-${Math.random().toString(36).slice(2, 7)}`;

  return (
    <label
      htmlFor={toggleId}
      className={cn(
        'flex items-center gap-3 cursor-pointer group',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      <button
        id={toggleId}
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => !disabled && onChange(!checked)}
        className={cn(
          'relative inline-flex flex-shrink-0 rounded-full border-2 border-transparent',
          'transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50',
          size === 'sm' && 'h-5 w-9',
          size === 'md' && 'h-6 w-11',
          checked ? 'bg-gradient-to-r from-rose-500 to-rose-600' : 'bg-surface-raised border-border',
        )}
      >
        <span
          className={cn(
            'pointer-events-none inline-block rounded-full bg-white shadow-md',
            'transform transition-transform duration-200',
            size === 'sm' && 'h-4 w-4',
            size === 'md' && 'h-5 w-5',
            checked
              ? size === 'sm'
                ? 'translate-x-4'
                : 'translate-x-5'
              : 'translate-x-0',
          )}
        />
      </button>
      {(label || description) && (
        <div className="flex flex-col">
          {label && (
            <span className="text-sm font-medium text-text-primary group-hover:text-text-primary transition-colors">
              {label}
            </span>
          )}
          {description && (
            <span className="text-xs text-text-muted">{description}</span>
          )}
        </div>
      )}
    </label>
  );
}

export { Toggle };
