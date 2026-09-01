'use client';

import { useState } from 'react';
import { UploadIllustration } from '@/components/illustrations/UploadIllustration';

export function UploadDropzone({ onFile }: { onFile: (file: File) => void }) {
  const [dragging, setDragging] = useState(false);
  const handleFile = (file?: File) => {
    if (!file || file.size > 10 * 1024 * 1024) return;
    onFile(file);
  };
  return <label htmlFor="incident-file" className={`border-2 border-dashed border-[var(--color-border)] rounded-[var(--radius-md)] p-12 flex flex-col items-center gap-4 cursor-pointer hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)] transition-all duration-150 ${dragging ? 'scale-[1.01] border-[var(--color-accent)] bg-[var(--color-accent-soft)]' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); handleFile(event.dataTransfer.files[0]); }}><input id="incident-file" type="file" accept=".txt,.json,.md,.pdf" className="sr-only" onChange={(event) => handleFile(event.target.files?.[0])} /><UploadIllustration className="w-16 h-16" /><div className="text-center"><p className="text-sm font-medium text-[var(--color-text-primary)]">Click to upload or drag and drop</p><p className="text-xs text-[var(--color-text-secondary)] mt-1">Supports .txt, .json, .md, .pdf (Max 10MB)</p></div></label>;
}
