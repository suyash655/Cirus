'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, ChevronRight } from 'lucide-react';
import { Reveal } from './motion-primitives';
import { duration, ease } from '@/lib/motion/tokens';

const STAGES = [
  {
    id: 'upload',
    step: '01',
    label: 'Upload Incident',
    description: 'Paste your incident report, CloudTrail export, or Slack thread.',
    icon: '📋',
  },
  {
    id: 'extract',
    step: '02',
    label: 'AI Extracts Structure',
    description: 'Model parses provider, severity, timeline, and affected services.',
    icon: '⚡',
  },
  {
    id: 'root-cause',
    step: '03',
    label: 'System Identifies Root Cause',
    description: 'Pinpoints the exact failure mechanism with citations and confidence scoring.',
    icon: '🔍',
  },
  {
    id: 'generate',
    step: '04',
    label: 'Generate Guardrails',
    description: 'Creates OPA policies, Terraform patches, and alerts simultaneously.',
    icon: '🛡️',
  },
  {
    id: 'approve',
    step: '05',
    label: 'Human Approves & Exports',
    description: 'Review the generated code, request changes, and export to GitHub.',
    icon: '👤',
  },
];

export function WorkflowPreview() {
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStep((p) => (p + 1) % STAGES.length);
    }, 3500); // Slower, more relaxed pacing
    return () => clearInterval(timer);
  }, []);

  const stage = STAGES[activeStep];

  return (
    <section className="relative py-24 lg:py-32 overflow-hidden border-t border-border-dim bg-bg-surface" aria-labelledby="workflow-heading">
      <div className="max-w-7xl mx-auto px-6 lg:px-12">
        <Reveal className="flex flex-col items-center text-center gap-4 mb-16 lg:mb-24">
          <span className="text-[11px] font-mono tracking-widest text-text-muted uppercase">
            How it works
          </span>
          <h2 id="workflow-heading" className="text-3xl lg:text-4xl font-medium tracking-tight text-text-primary">
            A structured workflow for <br className="hidden sm:block" />
            unstructured data.
          </h2>
          <p className="text-lg text-text-secondary max-w-xl">
            Cirus doesn't just chat. It runs your incident through a rigorous 5-step deterministic pipeline.
          </p>
        </Reveal>

        <div className="grid lg:grid-cols-[1fr_380px] gap-12 lg:gap-16 items-start">
          <div className="flex flex-col gap-2" role="tablist" aria-label="Workflow stages">
            {STAGES.map((s, i) => {
              const isActive = i === activeStep;
              const isDone = i < activeStep;

              return (
                <button
                  key={s.id}
                  onClick={() => setActiveStep(i)}
                  role="tab"
                  aria-selected={isActive}
                  aria-controls={`stage-panel-${s.id}`}
                  id={`stage-tab-${s.id}`}
                  className="flex items-center gap-4 p-4 rounded-xl text-left transition-all duration-300 w-full group relative outline-none focus-visible:ring-2 focus-visible:ring-text-primary"
                  style={{
                    background: isActive ? 'hsl(var(--bg-base))' : 'transparent',
                    border: '1px solid',
                    borderColor: isActive ? 'hsl(var(--border-strong))' : 'transparent',
                    boxShadow: isActive ? '0 2px 8px hsl(0 0% 0% / 0.04)' : 'none',
                  }}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 text-lg transition-all duration-300"
                    style={{
                      background: isActive
                        ? 'hsl(var(--bg-surface))'
                        : isDone
                          ? 'transparent'
                          : 'hsl(var(--bg-base))',
                      border: `1px solid ${isActive ? 'hsl(var(--border-strong))' : isDone ? 'transparent' : 'hsl(var(--border-dim))'}`,
                    }}
                  >
                    {isDone ? <Check className="w-5 h-5 text-text-muted" /> : <span className={isActive ? '' : 'opacity-40'}>{s.icon}</span>}
                  </div>
                  
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-mono font-bold uppercase tracking-wider" style={{ color: isActive ? 'hsl(var(--text-primary))' : 'hsl(var(--text-faint))' }}>
                        {s.step}
                      </span>
                      <span className="text-[15px] font-semibold truncate transition-colors duration-300" style={{ color: isActive ? 'hsl(var(--text-primary))' : 'hsl(var(--text-secondary))' }}>
                        {s.label}
                      </span>
                    </div>
                    <AnimatePresence initial={false}>
                      {isActive && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }} 
                          animate={{ opacity: 1, height: 'auto' }} 
                          exit={{ opacity: 0, height: 0 }}
                          transition={{ duration: duration.standard, ease }}
                          className="text-[13px] text-text-secondary leading-relaxed pr-4 overflow-hidden"
                        >
                          <div className="pt-1 pb-2">{s.description}</div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  
                  <div className="w-5 h-5 flex items-center justify-center opacity-0 transition-opacity duration-300" style={{ opacity: isActive ? 1 : 0 }}>
                    <ChevronRight className="w-4 h-4 text-text-primary" />
                  </div>
                </button>
              );
            })}
          </div>

          <div className="lg:sticky lg:top-24 hidden lg:block">
            <AnimatePresence mode="wait">
              <motion.div
                key={stage.id}
                role="tabpanel"
                aria-labelledby={`stage-tab-${stage.id}`}
                initial={{ opacity: 0, y: 16, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -16, scale: 0.98 }}
                transition={{ duration: duration.standard, ease }}
                className="rounded-2xl p-8 aspect-square flex flex-col items-center justify-center text-center bg-bg-base border border-border-base shadow-sm"
              >
                <div
                  className="w-16 h-16 rounded-xl flex items-center justify-center text-3xl mb-6 bg-bg-surface border border-border-dim"
                  aria-hidden="true"
                >
                  {stage.icon}
                </div>
                <h3 className="text-[17px] font-semibold text-text-primary mb-3">{stage.label}</h3>
                <p className="text-[14px] text-text-secondary leading-relaxed max-w-[240px] mx-auto">{stage.description}</p>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </section>
  );
}
