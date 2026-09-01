'use client';

import { Layers, Search, Database, Cloud, ShieldCheck } from 'lucide-react';
import { StaggerGroup, Reveal } from './motion-primitives';

const TECH_STACK = [
  { name: 'Featherless AI', icon: Layers,  desc: 'Serverless LLM Inference' },
  { name: 'Firecrawl',      icon: Search,  desc: 'Context Retrieval' },
  { name: 'Wolfram',        icon: Database,desc: 'Risk Scoring' },
  { name: 'Render',         icon: Cloud,   desc: 'Platform Deployment' },
  { name: 'Policy Export',  icon: ShieldCheck, desc: 'OPA / Rego Integration' },
];

export function TechStrip() {
  return (
    <section className="py-16 border-t border-border-dim bg-bg-surface relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-12 flex flex-col items-center">
        <Reveal>
          <p className="text-[11px] font-mono uppercase tracking-widest text-text-muted mb-10 text-center">
            Powered by modern infrastructure
          </p>
        </Reveal>
        
        <StaggerGroup className="flex flex-wrap justify-center items-center gap-x-12 gap-y-8">
          {TECH_STACK.map((tech) => {
            const Icon = tech.icon;
            return (
              <div
                key={tech.name}
                className="flex items-center gap-3 group cursor-default"
              >
                <div className="w-10 h-10 rounded-lg bg-bg-base border border-border-dim flex items-center justify-center group-hover:border-border-strong transition-colors duration-300">
                  <Icon className="w-5 h-5 text-text-muted group-hover:text-text-primary transition-colors duration-300" />
                </div>
                <div>
                  <h4 className="text-[14px] font-semibold text-text-secondary group-hover:text-text-primary transition-colors duration-300">{tech.name}</h4>
                  <p className="text-[10px] text-text-muted uppercase tracking-wider font-medium">{tech.desc}</p>
                </div>
              </div>
            );
          })}
        </StaggerGroup>
      </div>
    </section>
  );
}
