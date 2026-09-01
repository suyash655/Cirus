'use client';

import { Bot, GitMerge, X, Check } from 'lucide-react';
import { Reveal } from './motion-primitives';

export function ComparisonSection() {
  return (
    <section className="py-24 lg:py-32 bg-bg-base relative overflow-hidden border-t border-border-dim">
      <div className="max-w-6xl mx-auto px-6 lg:px-12">
        <Reveal className="text-center mb-16 lg:mb-24">
          <h2 className="text-3xl lg:text-4xl font-medium text-text-primary mb-4">
            Why not just use a chat prompt?
          </h2>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto">
            Generic LLMs hallucinate code and lack context. Cirus uses a deterministic pipeline designed specifically for cloud infrastructure.
          </p>
        </Reveal>

        <div className="grid md:grid-cols-2 gap-6 lg:gap-12">
          {/* ChatGPT / Generic approach */}
          <Reveal delay={0.1}>
            <div className="h-full rounded-xl lg:rounded-2xl p-6 lg:p-10 border border-border-dim bg-bg-surface flex flex-col gap-6 lg:gap-8 opacity-60">
              <div className="flex items-center gap-3 lg:gap-4 pb-4 lg:pb-6 border-b border-border-dim">
                <div className="w-10 h-10 lg:w-12 lg:h-12 rounded-xl bg-bg-base flex items-center justify-center text-text-muted border border-border-dim">
                  <Bot className="w-5 h-5 lg:w-6 lg:h-6" />
                </div>
                <div>
                  <h3 className="text-[15px] lg:text-[17px] font-semibold text-text-primary">Generic LLM Prompt</h3>
                  <p className="text-[12px] lg:text-[13px] text-text-muted">Chat UI</p>
                </div>
              </div>
              
              <ul className="flex flex-col gap-4 lg:gap-5">
                {[
                  'Hallucinates Terraform syntax',
                  'No access to historical incidents',
                  'Requires writing complex prompts',
                  'Outputs raw text, not ready-to-merge files',
                  'No automated syntax validation'
                ].map((text, i) => (
                  <li key={i} className="flex items-start gap-3 lg:gap-4 text-[13px] lg:text-[14px] text-text-secondary">
                    <X className="w-4 h-4 text-text-muted mt-0.5 flex-shrink-0" />
                    {text}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          {/* Cirus Pipeline approach */}
          <Reveal delay={0.2}>
            <div className="h-full rounded-xl lg:rounded-2xl p-6 lg:p-10 border border-border-strong bg-bg-base flex flex-col gap-6 lg:gap-8 relative shadow-sm">
              <div className="flex items-center gap-3 lg:gap-4 pb-4 lg:pb-6 border-b border-border-dim relative z-10">
                <div className="w-10 h-10 lg:w-12 lg:h-12 rounded-xl bg-bg-surface flex items-center justify-center border border-border-strong">
                  <GitMerge className="w-5 h-5 lg:w-6 lg:h-6 text-text-primary" />
                </div>
                <div>
                  <h3 className="text-[15px] lg:text-[17px] font-semibold text-text-primary">Cirus Workflow</h3>
                  <p className="text-[12px] lg:text-[13px] font-medium text-text-secondary">Deterministic Pipeline</p>
                </div>
              </div>
              
              <ul className="flex flex-col gap-4 lg:gap-5 relative z-10">
                {[
                  'Strict structural extraction (Provider, Severity)',
                  'Retrieval Augmented Generation (RAG) on cloud docs',
                  'Dedicated Critic Model validates OPA/TF syntax',
                  'Outputs directly exportable file diffs',
                  'Risk scoring and human-approval gates built in'
                ].map((text, i) => (
                  <li key={i} className="flex items-start gap-3 lg:gap-4 text-[13px] lg:text-[14px] text-text-primary font-medium">
                    <Check className="w-4 h-4 text-text-primary mt-0.5 flex-shrink-0" />
                    {text}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
