'use client';

import { Shield, FileCode2, Bell, BookOpen, FlaskConical, Search, Target, Activity, Users } from 'lucide-react';
import { Reveal, StaggerGroup, SpotlightCard } from './motion-primitives';

const FEATURES = [
  {
    icon: Search,
    title: 'Root Cause Extraction',
    description: 'AI extracts the exact root cause with cited evidence and timeline reconstruction.',
    tag: 'RCA',
  },
  {
    icon: Shield,
    title: 'Policy-as-Code',
    description: 'Generates OPA/Rego rules or AWS SCPs that enforce the fix permanently.',
    tag: 'OPA · SCP',
  },
  {
    icon: FileCode2,
    title: 'IaC Patch Suggestions',
    description: 'Produces Terraform or CDK diffs with exact resource changes, ready to merge.',
    tag: 'Terraform · CDK',
  },
  {
    icon: Bell,
    title: 'Monitoring & Alerts',
    description: 'Creates Prometheus or CloudWatch alert rules to detect similar issues fast.',
    tag: 'Prometheus · CW',
  },
  {
    icon: BookOpen,
    title: 'Runbooks',
    description: 'Step-by-step operational guides for on-call engineers with escalation paths.',
    tag: 'On-call',
  },
  {
    icon: FlaskConical,
    title: 'Regression Tests',
    description: 'Automated test cases to validate the fix never regresses.',
    tag: 'pytest · Jest',
  },
  {
    icon: Target,
    title: 'Citations & Evidence',
    description: 'Every generated artifact is backed by verifiable citations from your logs.',
    tag: 'Traceability',
  },
  {
    icon: Activity,
    title: 'Risk Scoring',
    description: 'Calculates incident severity and measures the exact risk reduction post-fix.',
    tag: 'Metrics',
  },
  {
    icon: Users,
    title: 'Human Approval Loop',
    description: 'Nothing ships without review. Approve, reject, or request changes easily.',
    tag: 'Governance',
  }
];

export function Features() {
  return (
    <section className="relative py-24 lg:py-32 overflow-hidden bg-bg-base" aria-labelledby="features-heading">
      <div className="absolute inset-0 bg-grid" style={{ backgroundSize: '32px 32px', opacity: 0.15 }} />

      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-12">
        <Reveal className="flex flex-col items-center text-center gap-4 mb-16 lg:mb-24">
          <span className="text-[11px] font-mono tracking-widest text-text-muted uppercase">
            Features
          </span>
          <h2 id="features-heading" className="text-3xl lg:text-4xl font-medium tracking-tight text-text-primary max-w-3xl">
            A complete platform for incident prevention.
          </h2>
          <p className="text-lg text-text-secondary max-w-2xl leading-relaxed">
            Everything you need to turn a postmortem document into concrete, enforceable infrastructure guardrails.
          </p>
        </Reveal>

        <StaggerGroup className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((feat) => {
            const Icon = feat.icon;

            return (
              <SpotlightCard key={feat.title} className="flex flex-col h-full bg-bg-surface p-6 group">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-5 bg-bg-base border border-border-dim">
                  <Icon className="w-5 h-5 text-text-secondary" />
                </div>
                
                <div className="flex items-start justify-between gap-2 mb-2 mt-auto">
                  <h3 className="text-[15px] font-semibold text-text-primary">{feat.title}</h3>
                  <span className="shrink-0 text-[10px] font-mono font-medium text-text-muted border border-border-dim px-2 py-0.5 rounded bg-bg-base">
                    {feat.tag}
                  </span>
                </div>
                
                <p className="text-[14px] text-text-secondary leading-relaxed">
                  {feat.description}
                </p>
              </SpotlightCard>
            );
          })}
        </StaggerGroup>
      </div>
    </section>
  );
}
