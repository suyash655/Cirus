'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Zap } from 'lucide-react';
import { useCreateIncident } from '@/lib/hooks/use-incidents';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/shared/page-header';
import { ARTIFACT_META, cn, detectFormat } from '@/lib/utils';
import type { ArtifactType, CloudProvider, Severity } from '@/lib/types';
import { ProviderSelector } from '@/components/incident/ProviderSelector';
import { SeveritySelector } from '@/components/incident/SeveritySelector';
import { UploadDropzone } from '@/components/incident/UploadDropzone';

// ─── Artifact picker ──────────────────────────────────────────────────────────
function ArtifactPicker({
  selected, onChange,
}: { selected: ArtifactType[]; onChange: (v: ArtifactType[]) => void }) {
  const toggle = (t: ArtifactType) => {
    onChange(selected.includes(t) ? selected.filter(x => x !== t) : [...selected, t]);
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {(Object.keys(ARTIFACT_META) as ArtifactType[]).map((type) => {
        const meta = ARTIFACT_META[type];
        const isSelected = selected.includes(type);
        return (
          <button
            key={type}
            type="button"
            id={`artifact-${type}`}
            onClick={() => toggle(type)}
            className="flex items-center gap-2.5 p-3 rounded-xl text-left transition-all duration-150"
            style={{
              background: isSelected ? 'hsl(var(--bg-raised))' : 'hsl(var(--bg-surface))',
              border: `1px solid ${isSelected ? 'hsl(var(--border-strong))' : 'hsl(var(--border-base))'}`,
            }}
          >
            <span className="text-lg">{meta.emoji}</span>
            <div className="min-w-0">
              <p className="text-xs font-semibold" style={{ color: isSelected ? 'hsl(var(--text-primary))' : 'hsl(var(--text-secondary))' }}>
                {meta.shortLabel}
              </p>
              <p className="text-[10px] text-text-muted truncate">{meta.fileExt}</p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

// ─── Processing animation ─────────────────────────────────────────────────────
const PROCESSING_STEPS = [
  { label: 'Queued' },
  { label: 'Normalizing incident data…' },
  { label: 'Classifying root cause…' },
  { label: 'Enriching context…' },
  { label: 'Generating artifacts…' },
  { label: 'Validating outputs…' },
  { label: 'Ready for review' },
];

const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};

const staggerItem = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] } },
};

function ProcessingOverlay({ step }: { step: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="absolute inset-0 z-10 flex flex-col items-center justify-center rounded-2xl gap-6"
      style={{ background: 'hsl(var(--bg-surface) / 0.96)', backdropFilter: 'blur(8px)' }}
    >
      <div className="w-14 h-14 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface)] flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-text-primary animate-spin" />
      </div>
      <div className="flex flex-col items-center gap-2">
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="text-sm font-medium text-text-primary"
          >
            {PROCESSING_STEPS[step % PROCESSING_STEPS.length].label}
          </motion.p>
        </AnimatePresence>
        <p className="text-xs text-text-muted">Processing your incident report…</p>
      </div>
      <div className="flex items-center gap-1.5">
        {PROCESSING_STEPS.map((_, i) => (
          <div
            key={i}
            className="h-1 rounded-full transition-all duration-500"
            style={{
              width: i === step % PROCESSING_STEPS.length ? 24 : 6,
              background: i === step % PROCESSING_STEPS.length ? 'hsl(var(--text-primary))' : 'hsl(var(--border-strong))',
            }}
          />
        ))}
      </div>
    </motion.div>
  );
}

// ─── Main form ────────────────────────────────────────────────────────────────
export default function NewIncidentPage() {
  const router = useRouter();
  const { mutateAsync: createIncident, isPending } = useCreateIncident();
  const [processingStep, setProcessingStep] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const [form, setForm] = useState({
    title: '',
    rawText: '',
    provider: 'AWS' as CloudProvider,
    severity: 'P3' as Severity,
    selectedArtifacts: Object.keys(ARTIFACT_META) as ArtifactType[],
    affectedServices: '',
    configSnippet: '',
    inputMethod: 'paste' as 'paste' | 'upload',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const validate = () => {
    const e: Record<string, string> = {};
    if (!form.title.trim()) e.title = 'Incident title is required';
    if (!form.rawText.trim()) e.rawText = 'Incident report text is required';
    if (form.selectedArtifacts.length === 0) e.artifacts = 'Select at least one artifact type';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsProcessing(true);

    // Animate processing steps
    const stepInterval = setInterval(() => {
      setProcessingStep((p) => p + 1);
    }, 700);

    try {
      const { id } = await createIncident({
        title: form.title,
        rawText: form.rawText,
        inputMethod: form.inputMethod,
        selectedArtifacts: form.selectedArtifacts,
        provider: form.provider,
        severity: form.severity,
      });
      clearInterval(stepInterval);
      setTimeout(() => router.push(`/incidents/${id}`), 600);
    } catch {
      clearInterval(stepInterval);
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg)] px-8 py-10 max-w-[900px] mx-auto">
      <PageHeader
        title="New Incident"
        description="Provide your incident report and Cirus will generate prevention artifacts."
      />

      <motion.form variants={staggerContainer} initial="hidden" animate="show" onSubmit={handleSubmit} className="relative">
        <AnimatePresence>
          {isProcessing && <ProcessingOverlay step={processingStep} />}
        </AnimatePresence>

        <div className="flex flex-col gap-7">

          {/* ── Title ── */}
          <motion.section variants={staggerItem}>
            <Input
              id="incident-title"
              label="Incident Title *"
              placeholder="e.g. S3 Public Access Exposure in Prod"
              value={form.title}
              onChange={(e) => setForm(f => ({ ...f, title: e.target.value }))}
              error={errors.title}
            />
          </motion.section>

          {/* ── Cloud provider ── */}
          <motion.section variants={staggerItem}>
            <label className="block text-sm font-semibold text-text-primary mb-3">
              Cloud Provider
            </label>
            <ProviderSelector value={form.provider} onChange={(v) => setForm(f => ({ ...f, provider: v }))} />
          </motion.section>

          {/* ── Severity ── */}
          <motion.section variants={staggerItem}>
            <label className="block text-sm font-semibold text-text-primary mb-3">
              Severity Level
            </label>
            <SeveritySelector value={form.severity} onChange={(v) => setForm(f => ({ ...f, severity: v }))} />
          </motion.section>

          {/* ── Incident text ── */}
          <motion.section variants={staggerItem}>
            <Textarea
              id="incident-text"
              label="Incident Report *"
              rows={10}
              placeholder="Paste your incident report here — CloudTrail logs, post-mortem notes, alert descriptions, or any free-form text…"
              value={form.rawText}
              onChange={(e) => setForm(f => ({ ...f, rawText: e.target.value }))}
              error={errors.rawText}
              hint={`${form.rawText.length} chars — Format detected: ${form.rawText ? detectFormat(form.rawText) : 'none'}`}
              showCharCount
              maxChars={50000}
              autoResize={false}
              style={{ minHeight: 220, fontFamily: 'monospace' }}
            />
            
            <div className="mt-4"><UploadDropzone onFile={(file) => { void file.text().then((text) => setForm((current) => ({ ...current, rawText: text || current.rawText || `Uploaded file: ${file.name}`, inputMethod: 'upload' }))); }} /></div>
          </motion.section>

          {/* ── Affected services ── */}
          <motion.section variants={staggerItem}>
            <Input
              id="affected-services"
              label="Affected Services (optional)"
              placeholder="e.g. S3, CloudFront, Lambda, RDS"
              value={form.affectedServices}
              onChange={(e) => setForm(f => ({ ...f, affectedServices: e.target.value }))}
              hint="Comma-separated list of services or resource names"
            />
          </motion.section>

          {/* ── Config snippet ── */}
          <motion.section variants={staggerItem}>
            <Textarea
              id="config-snippet"
              label="Terraform / Config Snippet (optional)"
              rows={6}
              placeholder="Paste relevant Terraform, CloudFormation, or config file content…"
              value={form.configSnippet}
              onChange={(e) => setForm(f => ({ ...f, configSnippet: e.target.value }))}
              hint="Helps generate more accurate IaC patches"
              style={{ fontFamily: 'monospace', fontSize: '12px' }}
            />
          </motion.section>

          {/* ── Artifact selection ── */}
          <motion.section variants={staggerItem}>
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-semibold text-text-primary">
                Artifact Types to Generate
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  id="select-all-artifacts"
                  onClick={() => setForm(f => ({ ...f, selectedArtifacts: Object.keys(ARTIFACT_META) as ArtifactType[] }))}
                  className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] transition-colors"
                >
                  All
                </button>
                <span className="text-text-faint text-xs">·</span>
                <button
                  type="button"
                  id="clear-artifacts"
                  onClick={() => setForm(f => ({ ...f, selectedArtifacts: [] }))}
                  className="text-xs text-text-muted hover:text-danger transition-colors"
                >
                  None
                </button>
              </div>
            </div>
            <ArtifactPicker
              selected={form.selectedArtifacts}
              onChange={(v) => setForm(f => ({ ...f, selectedArtifacts: v }))}
            />
            {errors.artifacts && (
              <p className="text-xs text-danger mt-2">{errors.artifacts}</p>
            )}
          </motion.section>

          {/* ── Submit ── */}
          <div className="flex items-center gap-4 pt-2">
            <button
              type="submit"
              id="submit-incident"
              disabled={isPending || isProcessing}
              className="inline-flex items-center gap-2.5 font-semibold h-11 px-7 rounded-lg bg-inverse-bg text-inverse-text text-sm hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isPending || isProcessing ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Analyzing…</>
              ) : (
                <><Zap className="w-4 h-4" /> Analyze Incident</>
              )}
            </button>

            <button
              type="button"
              onClick={() => router.back()}
              className="text-sm text-text-muted hover:text-text-secondary transition-colors"
              id="cancel-incident"
            >
              Cancel
            </button>

            {form.selectedArtifacts.length > 0 && (
              <span className="text-xs text-text-faint ml-auto">
                {form.selectedArtifacts.length} artifact{form.selectedArtifacts.length !== 1 ? 's' : ''} selected
              </span>
            )}
          </div>
        </div>
      </motion.form>
    </div>
  );
}
