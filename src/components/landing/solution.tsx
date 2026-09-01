'use client';

import { Shield, ArrowRight, Check } from 'lucide-react';
import { Reveal } from './motion-primitives';

export function SolutionSection() {
  return (
    <section className="relative py-24 lg:py-32 overflow-hidden bg-bg-base" aria-labelledby="solution-heading">
      <div className="max-w-7xl mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          
          {/* Visual Representation */}
          <Reveal className="relative order-2 lg:order-1">
            <div className="relative bg-bg-surface rounded-2xl p-8 border border-border-base shadow-sm">
              <div className="flex items-center gap-4 mb-6 pb-6 border-b border-border-dim">
                <div className="w-10 h-10 rounded-lg bg-bg-base flex items-center justify-center border border-border-base">
                  <Shield className="w-5 h-5 text-text-secondary" />
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold text-text-primary">The Cirus Workflow</h3>
                  <p className="text-[13px] text-text-muted">Automated prevention</p>
                </div>
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3 p-4 rounded-xl bg-bg-base border border-border-dim">
                  <span className="text-[15px]">📋</span>
                  <span className="text-[13px] text-text-secondary font-medium">1. Upload postmortem</span>
                </div>
                <div className="flex justify-center -my-1 relative z-10">
                  <div className="bg-bg-surface px-2">
                    <ArrowRight className="w-3 h-3 text-border-strong transform rotate-90" />
                  </div>
                </div>
                <div className="flex flex-col gap-3 p-5 rounded-xl bg-bg-raised border border-border-strong">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-[11px] font-bold text-text-primary uppercase tracking-widest">2. AI Pipeline generates:</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {['OPA Policies', 'Terraform Patches', 'Alert Rules', 'Runbooks'].map((item) => (
                      <div key={item} className="flex items-center gap-2 text-[12px] font-medium text-text-secondary bg-bg-base px-2.5 py-1.5 rounded-lg border border-border-dim">
                        <Check className="w-3.5 h-3.5 text-text-primary" />
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1} className="flex flex-col gap-6 order-1 lg:order-2">
            <span className="text-[11px] font-mono tracking-widest text-text-muted uppercase">
              The Solution
            </span>
            <h2 id="solution-heading" className="text-3xl lg:text-4xl font-medium tracking-tight text-text-primary leading-[1.15]">
              Convert incident text into enforceable cloud guardrails.
            </h2>
            <p className="text-lg text-text-secondary leading-relaxed">
              Cirus uses a specialized AI workflow to read your postmortems and automatically generate the exact code needed to prevent the outage from happening again. Instead of ignoring action items, your team reviews and merges generated policies directly into your codebase.
            </p>
          </Reveal>

        </div>
      </div>
    </section>
  );
}
