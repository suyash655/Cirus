'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  hint?: string;
  autoResize?: boolean;
  showCharCount?: boolean;
  maxChars?: number;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      label,
      error,
      hint,
      autoResize = false,
      showCharCount = false,
      maxChars,
      className,
      id,
      onChange,
      value,
      ...props
    },
    ref,
  ) => {
    const inputId = id ?? `textarea-${Math.random().toString(36).slice(2, 7)}`;
    const [charCount, setCharCount] = React.useState(
      typeof value === 'string' ? value.length : 0,
    );

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setCharCount(e.target.value.length);
      if (autoResize) {
        e.target.style.height = 'auto';
        e.target.style.height = `${e.target.scrollHeight}px`;
      }
      onChange?.(e);
    };

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-text-secondary">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={inputId}
          value={value}
          onChange={handleChange}
          className={cn(
            'w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)]',
            'px-4 py-3 text-sm text-[var(--color-text-primary)] font-mono',
            'placeholder:text-[var(--color-text-tertiary)] placeholder:font-sans',
            'focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent-soft)]',
            'transition-colors duration-150 outline-none resize-y',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            error && 'border-danger focus:border-danger focus:ring-danger/30',
            autoResize && 'resize-none overflow-hidden',
            className,
          )}
          {...props}
        />
        <div className="flex items-center justify-between">
          <div>
            {error && <p className="text-xs text-danger">{error}</p>}
            {hint && !error && <p className="text-xs text-text-muted">{hint}</p>}
          </div>
          {showCharCount && (
            <p
              className={cn(
                'text-xs tabular-nums',
                maxChars && charCount > maxChars ? 'text-danger' : 'text-text-muted',
              )}
            >
              {charCount.toLocaleString()}
              {maxChars && ` / ${maxChars.toLocaleString()}`}
            </p>
          )}
        </div>
      </div>
    );
  },
);

Textarea.displayName = 'Textarea';

export { Textarea };
