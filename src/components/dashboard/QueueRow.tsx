'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, Archive, Clipboard, Download } from 'lucide-react';
import type { Artifact, ArtifactSet, ArtifactType, Incident } from '@/lib/types';
import { useArtifacts } from '@/lib/hooks/use-incidents';
import { artifactText, downloadAllArtifacts, downloadArtifact } from '@/lib/downloadArtifact';
import { ApproveButton } from './ApproveButton';

const tabs: Array<{ type: ArtifactType; label: string; filename: string }> = [
  { type: 'rca',        label: 'RCA',        filename: 'rca.md' },
  { type: 'policy',     label: 'OPA Policy', filename: 'guardrail.rego' },
  { type: 'iac',        label: 'Terraform',  filename: 'remediation.tf' },
  { type: 'alerts',     label: 'Alert Rule', filename: 'alerts.yaml' },
  { type: 'runbook',    label: 'Runbook',    filename: 'runbook.md' },
  { type: 'regression', label: 'Regression', filename: 'regression-tests.txt' },
];

function SevPill({ sev }: { sev: string }) {
  const cls = sev === 'P1' ? 'c-sev-p1' : sev === 'P2' ? 'c-sev-p2' : sev === 'P3' ? 'c-sev-p3' : 'c-sev-p4';
  return <span className={cls}>{sev}</span>;
}

export function QueueRow({
  incident,
  onApprove,
}: {
  incident: Incident;
  onApprove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [active, setActive]     = useState<ArtifactType>('rca');
  const { data: artifacts }     = useArtifacts(expanded ? incident.id : '');
  const entries = Object.entries(artifacts ?? {}) as Array<[ArtifactType, Artifact]>;
  const availableTabs = tabs.filter(({ type }) => Boolean((artifacts as ArtifactSet | undefined)?.[type]));
  const current       = (artifacts as ArtifactSet | undefined)?.[active];

  return (
    <div
      className="rounded-[12px] overflow-hidden"
      style={{ border: '1px solid var(--color-border)' }}
    >
      {/* Row header */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full h-14 px-6 flex items-center gap-4 text-left transition-colors duration-150"
        style={{ background: expanded ? 'var(--color-bg)' : 'var(--color-surface)' }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = 'var(--color-bg)')}
        onMouseLeave={(e) => {
          if (!expanded) (e.currentTarget as HTMLElement).style.background = 'var(--color-surface)';
        }}
      >
        <span
          className="flex-1 min-w-0 truncate text-[13px] font-medium"
          style={{ color: 'var(--color-text-primary)' }}
        >
          {incident.title}
        </span>
        <SevPill sev={incident.severity} />
        <span
          className="hidden md:block w-44 truncate text-[12px]"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {incident.summary}
        </span>
        <span className="c-pill-partial text-[11px]">Awaiting</span>
        <ChevronDown
          size={16}
          className={`transition-transform duration-150 ${expanded ? 'rotate-180' : ''}`}
          style={{ color: 'var(--color-text-muted)' }}
        />
      </button>

      {/* Expanded content */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            style={{ borderTop: '1px solid var(--color-border)' }}
          >
            <div className="p-6">
              {availableTabs.length > 0 ? (
                <>
                  {/* Tab bar */}
                  <div className="flex flex-wrap gap-1" style={{ borderBottom: '1px solid var(--color-border)', marginBottom: 16 }}>
                    {availableTabs.map((tab) => (
                      <button
                        key={tab.type}
                        type="button"
                        onClick={() => setActive(tab.type)}
                        className="px-3 py-2 text-[12px] font-medium border-b-2 transition-colors"
                        style={{
                          borderBottomColor: active === tab.type ? 'var(--color-accent)' : 'transparent',
                          color: active === tab.type ? 'var(--color-accent)' : 'var(--color-text-secondary)',
                        }}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  {/* Code preview */}
                  {current && (
                    <div className="rounded-[8px] overflow-hidden" style={{ border: '1px solid var(--color-border-strong)', background: 'var(--color-code-bg)' }}>
                      <div
                        className="h-10 px-4 flex items-center gap-3 text-[12px]"
                        style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--color-code-text)' }}
                      >
                        <span className="font-mono">{availableTabs.find((t) => t.type === active)?.filename}</span>
                        <span className="ml-auto flex gap-3">
                          <button
                            type="button"
                            title="Copy"
                            onClick={() => navigator.clipboard.writeText(artifactText(current))}
                            style={{ color: 'var(--color-code-text)', opacity: 0.6 }}
                          >
                            <Clipboard size={14} />
                          </button>
                          <button
                            type="button"
                            title="Download"
                            onClick={() => downloadArtifact(
                              availableTabs.find((t) => t.type === active)?.filename ?? 'artifact.txt',
                              artifactText(current),
                            )}
                            style={{ color: 'var(--color-code-text)', opacity: 0.6 }}
                          >
                            <Download size={14} />
                          </button>
                        </span>
                      </div>
                      <pre
                        className="p-4 max-h-64 overflow-auto whitespace-pre-wrap text-[12px] leading-5"
                        style={{ color: 'var(--color-code-text)' }}
                      >
                        <code>{artifactText(current)}</code>
                      </pre>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-[13px]" style={{ color: 'var(--color-text-secondary)' }}>
                  Artifacts are still being generated.
                </p>
              )}

              {/* Actions */}
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <ApproveButton onApprove={async () => { onApprove(); }} />
                <button
                  type="button"
                  className="c-btn-secondary c-btn-sm"
                >
                  Request Changes
                </button>
                <button
                  type="button"
                  className="text-[13px] transition-colors"
                  style={{ color: 'var(--color-danger)' }}
                >
                  Reject
                </button>
                <button
                  type="button"
                  onClick={() => downloadAllArtifacts(entries)}
                  className="ml-auto c-btn-secondary c-btn-sm inline-flex items-center gap-1.5"
                >
                  <Archive size={13} /> Download All (.zip)
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
