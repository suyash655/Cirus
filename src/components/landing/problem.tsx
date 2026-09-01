'use client';

import { ArrowRight, AlertCircle, FileText, Trash2 } from 'lucide-react';
import { Reveal } from './motion-primitives';

export function ProblemSection() {
  return (
    <section className="relative py-24 lg:py-32 overflow-hidden border-t border-border-dim bg-bg-surface" aria-labelledby="problem-heading">
      <div className="max-w-7xl mx-auto px-6 lg:px-12">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          
          <Reveal className="flex flex-col gap-6">
            <span className="text-[11px] font-mono tracking-widest text-text-muted uppercase">
              The Problem
            </span>
            <h2 id="problem-heading" className="text-3xl lg:text-4xl font-medium tracking-tight text-text-primary leading-[1.15]">
              Incidents repeat because knowledge is trapped in documents.
            </h2>
            <p className="text-lg text-text-secondary leading-relaxed">
              Teams spend hours writing detailed postmortems after an outage. But these PDFs and Jira tickets get filed away and forgotten. The learnings are never translated into actual infrastructure changes, causing the exact same incident to happen again six months later.
            </p>
          </Reveal>

          {/* Visual Representation */}
          <Reveal delay={0.1} className="relative">
            <div className="relative bg-bg-base rounded-2xl p-8 border border-border-base shadow-sm">
              <div className="flex items-center gap-4 mb-6 pb-6 border-b border-border-dim">
                <div className="w-10 h-10 rounded-lg bg-surface flex items-center justify-center border border-border-base">
                  <AlertCircle className="w-5 h-5 text-text-secondary" />
                </div>
                <div>
                  <h3 className="text-[15px] font-semibold text-text-primary">The Incident Cycle</h3>
                  <p className="text-[13px] text-text-muted">The traditional postmortem loop</p>
                </div>
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3 p-4 rounded-xl bg-bg-surface border border-border-dim">
                  <AlertCircle className="w-4 h-4 text-text-muted" />
                  <span className="text-[13px] text-text-secondary font-medium">1. Outage occurs & resolved</span>
                </div>
                <div className="flex justify-center -my-1 relative z-10">
                  <div className="bg-bg-base px-2">
                    <ArrowRight className="w-3 h-3 text-border-strong transform rotate-90" />
                  </div>
                </div>
                <div className="flex items-center justify-between p-4 rounded-xl bg-bg-surface border border-border-dim">
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-text-muted" />
                    <span className="text-[13px] text-text-secondary font-medium">2. Write 5-page postmortem</span>
                  </div>
                  <span className="text-[10px] font-medium text-text-muted border border-border-dim px-2 py-0.5 rounded bg-bg-base">Doc saved</span>
                </div>
                <div className="flex justify-center -my-1 relative z-10">
                  <div className="bg-bg-base px-2">
                    <ArrowRight className="w-3 h-3 text-border-strong transform rotate-90" />
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-xl bg-inverse-bg border border-inverse-bg text-inverse-text">
                  <Trash2 className="w-4 h-4 text-inverse-text opacity-70" />
                  <span className="text-[13px] font-medium">3. Action items ignored. Outage repeats.</span>
                </div>
              </div>
            </div>
          </Reveal>

        </div>
      </div>
    </section>
  );
}
