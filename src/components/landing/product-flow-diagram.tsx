'use client';

import { useScroll, useTransform, motion } from 'framer-motion';
import { useRef } from 'react';
import { 
  Upload, 
  Sparkles, 
  Shield, 
  FileCode2, 
  Bell, 
  BookOpen, 
  Check,
  ArrowRight
} from 'lucide-react';
import { Reveal } from './motion-primitives';

const FLOW_STEPS = [
  {
    id: 'upload',
    icon: Upload,
    title: 'Upload Incident',
    description: 'Paste your postmortem, CloudTrail export, or Slack thread',
  },
  {
    id: 'extract',
    icon: Sparkles,
    title: 'AI Extraction',
    description: 'Parse provider, severity, timeline, and affected services',
  },
  {
    id: 'rca',
    icon: Shield,
    title: 'Root Cause Analysis',
    description: 'Identify failure mechanism with citations and confidence',
  },
  {
    id: 'artifacts',
    icon: FileCode2,
    title: 'Generate Artifacts',
    description: 'Create OPA policies, Terraform patches, and alerts',
  },
  {
    id: 'monitoring',
    icon: Bell,
    title: 'Monitoring Rules',
    description: 'Deploy Prometheus/CloudWatch alerts for detection',
  },
  {
    id: 'runbook',
    icon: BookOpen,
    title: 'Runbook Generation',
    description: 'Step-by-step operational guides with escalation paths',
  },
  {
    id: 'complete',
    icon: Check,
    title: 'Ready to Deploy',
    description: 'All artifacts reviewed, approved, and exportable',
  },
];

export function ProductFlowDiagram() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start end', 'end start'],
  });

  const lineProgress = useTransform(scrollYProgress, [0, 0.8], [0, 1]);

  return (
    <section 
      ref={containerRef}
      className="relative py-24 lg:py-32 overflow-hidden bg-bg-base border-t border-border-dim"
      aria-labelledby="flow-heading"
    >
      <div className="max-w-5xl mx-auto px-6 lg:px-12">
        <Reveal className="text-center mb-16 lg:mb-24">
          <span className="text-[11px] font-mono tracking-widest text-text-muted uppercase mb-4 block">
            Complete Flow
          </span>
          <h2 id="flow-heading" className="text-3xl lg:text-4xl font-medium tracking-tight text-text-primary">
            From incident to infrastructure in minutes
          </h2>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto mt-4 leading-relaxed">
            Watch how Cirus transforms unstructured incident text into production-ready guardrails.
          </p>
        </Reveal>

        {/* Flow Diagram */}
        <div className="relative">
          {/* Progress Line */}
          <div className="absolute left-6 lg:left-1/2 top-0 bottom-0 w-px bg-border-dim lg:-translate-x-1/2">
            <motion.div 
              className="absolute top-0 left-0 w-full h-full bg-border-strong origin-top"
              style={{ scaleY: lineProgress }}
            />
          </div>

          {/* Flow Steps */}
          <div className="space-y-12 lg:space-y-16">
            {FLOW_STEPS.map((step, index) => {
              const Icon = step.icon;
              const isEven = index % 2 === 0;
              
              return (
                <Reveal key={step.id} delay={0.1}>
                  <div className={`relative flex items-center gap-6 lg:gap-12 pl-12 lg:pl-0 ${isEven ? 'lg:flex-row' : 'lg:flex-row-reverse'}`}>
                    
                    {/* Icon Node */}
                    <div className="absolute left-0 lg:static lg:flex-shrink-0 z-10 w-12 h-12 lg:w-16 lg:h-16 rounded-xl bg-bg-surface flex items-center justify-center border border-border-strong shadow-sm group">
                      <Icon className="w-5 h-5 lg:w-6 lg:h-6 text-text-secondary group-hover:text-text-primary transition-colors duration-300" />
                    </div>

                    {/* Content Card */}
                    <div className={`flex-1 bg-bg-surface rounded-xl p-6 border border-border-dim shadow-sm ${isEven ? 'lg:pr-8' : 'lg:pl-8'}`}>
                      <div className="flex items-start gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-text-muted border border-border-dim px-2 py-0.5 rounded bg-bg-base">
                              Step {index + 1}
                            </span>
                            <h3 className="text-[15px] font-semibold text-text-primary">
                              {step.title}
                            </h3>
                          </div>
                          <p className="text-[14px] text-text-secondary leading-relaxed">
                            {step.description}
                          </p>
                        </div>
                        
                        {index < FLOW_STEPS.length - 1 && (
                          <div className="hidden lg:flex items-center justify-center w-8 h-8 rounded-lg bg-bg-base border border-border-dim">
                            <ArrowRight className="w-4 h-4 text-text-muted" />
                          </div>
                        )}
                      </div>
                    </div>

                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>

        {/* Summary Box */}
        <Reveal delay={0.2} className="mt-20 lg:mt-32">
          <div className="rounded-2xl p-8 lg:p-10 border border-border-strong text-center bg-bg-surface shadow-sm">
            <div className="flex items-center justify-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-full bg-bg-base border border-border-strong flex items-center justify-center">
                <Check className="w-4 h-4 text-text-primary" />
              </div>
              <h3 className="text-[17px] font-semibold text-text-primary">
                Complete Prevention Pipeline
              </h3>
            </div>
            <p className="text-[14px] text-text-secondary max-w-xl mx-auto leading-relaxed">
              Every incident is processed through this deterministic workflow, ensuring consistent, 
              high-quality guardrails that actually prevent recurrence.
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}