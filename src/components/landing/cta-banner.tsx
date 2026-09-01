'use client';

import Link from 'next/link';
import { ArrowRight, Zap } from 'lucide-react';
import { Reveal } from './motion-primitives';

export function CTABanner() {
  return (
    <section className="relative py-32 overflow-hidden bg-bg-surface border-t border-border-dim">
      <div className="absolute inset-0 bg-grid" style={{ backgroundSize: '32px 32px', opacity: 0.15 }} />

      <div className="relative z-10 max-w-4xl mx-auto px-6 lg:px-12 text-center">
        <Reveal className="flex flex-col items-center gap-8">
          {/* Icon */}
          <div className="w-12 h-12 rounded-xl flex items-center justify-center bg-bg-base border border-border-strong shadow-sm">
            <Zap className="w-5 h-5 text-text-primary" />
          </div>

          <h2 className="text-4xl lg:text-5xl font-medium tracking-tight text-text-primary">
            Ready to prevent the next incident?
          </h2>

          <p className="text-lg text-text-secondary max-w-xl leading-relaxed">
            Upload your first incident report and get 6 production-ready prevention
            artifacts in under 2 minutes. No setup required.
          </p>

          <div className="flex items-center gap-4 flex-wrap justify-center mt-4">
            <Link href="/incidents/new" id="cta-banner-primary">
              <button className="inline-flex items-center gap-2.5 font-medium px-6 py-3 rounded-lg bg-inverse-bg text-inverse-text hover:opacity-90 transition-opacity outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-inverse-bg focus-visible:ring-offset-bg-surface">
                <Zap className="w-4 h-4" />
                Analyze an incident free
                <ArrowRight className="w-4 h-4" />
              </button>
            </Link>

            <Link href="/dashboard" id="cta-banner-secondary">
              <button className="inline-flex items-center gap-2 font-medium px-6 py-3 rounded-lg bg-bg-base border border-border-strong text-text-primary hover:bg-bg-raised transition-colors outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-text-primary focus-visible:ring-offset-bg-surface">
                View demo dashboard
                <ArrowRight className="w-4 h-4 text-text-muted" />
              </button>
            </Link>
          </div>

          {/* Trust line */}
          <p className="text-[11px] font-medium text-text-muted mt-4">
            No credit card. No account required for first incident. GDPR compliant.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
