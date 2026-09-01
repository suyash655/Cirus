'use client';

import * as React from 'react';
import { Check, Copy, Download } from 'lucide-react';
import { cn, copyToClipboard, downloadFile } from '@/lib/utils';

interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
  className?: string;
  downloadAs?: string;
}

function CodeBlock({
  code,
  language = 'text',
  filename,
  showLineNumbers = true,
  className,
  downloadAs,
}: CodeBlockProps) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    await copyToClipboard(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (downloadAs) downloadFile(code, downloadAs);
  };

  const lines = code.split('\n');

  return (
    <div
      className={cn(
        'group relative rounded-xl overflow-hidden border border-border',
        'code-surface',
        className,
      )}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border/50 bg-surface">
        <div className="flex items-center gap-3">
          {/* Traffic lights */}
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/70" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
          </div>
          {filename && (
            <span className="text-xs text-text-muted font-mono">{filename}</span>
          )}
          {language && (
            <span className="text-xs text-text-muted/60 font-mono uppercase">{language}</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {downloadAs && (
            <button
              onClick={handleDownload}
              title={`Download ${downloadAs}`}
              className={cn(
                'p-1.5 rounded-md transition-all duration-150',
                'text-text-muted hover:text-text-primary hover:bg-surface-raised',
              )}
            >
              <Download className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            onClick={handleCopy}
            title="Copy to clipboard"
            className={cn(
              'p-1.5 rounded-md transition-all duration-150',
              copied
                ? 'text-emerald-400'
                : 'text-text-muted hover:text-text-primary hover:bg-surface-raised',
            )}
          >
            {copied ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* Code body */}
      <div className="overflow-x-auto">
        <pre className="p-4 text-xs leading-relaxed font-mono text-text-secondary">
          {showLineNumbers ? (
            <code>
              {lines.map((line, i) => (
                <span key={i} className="flex">
                  <span className="select-none w-8 flex-shrink-0 text-right pr-4 text-text-muted/40">
                    {i + 1}
                  </span>
                  <span className={cn(
                    // Syntax color hints based on content
                    line.startsWith('+') && 'text-emerald-400',
                    line.startsWith('-') && 'text-rose-400',
                    line.startsWith('#') && 'text-text-muted italic',
                  )}>
                    {line || ' '}
                  </span>
                </span>
              ))}
            </code>
          ) : (
            <code>{code}</code>
          )}
        </pre>
      </div>
    </div>
  );
}

export { CodeBlock };
