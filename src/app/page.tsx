import type { Metadata } from 'next';
import Link from 'next/link';
import { Hero } from '@/components/landing/hero';
import { ProblemSection } from '@/components/landing/problem';
import { SolutionSection } from '@/components/landing/solution';
import { WorkflowPreview } from '@/components/landing/workflow-preview';
import { Features } from '@/components/landing/features';
import { SamplePreview } from '@/components/landing/sample-preview';
import { ComparisonSection } from '@/components/landing/comparison';
import { TechStrip } from '@/components/landing/tech-strip';
import { CTABanner } from '@/components/landing/cta-banner';
import { NavHeader } from '@/components/landing/nav-header';
import { ProductFlowDiagram } from '@/components/landing/product-flow-diagram';

export const metadata: Metadata = {
  title: 'Cirus — Turn Cloud Incidents Into Prevention',
  description:
    'Upload an incident report and generate enforceable guardrails, Terraform patches, alert rules, runbooks, and regression tests in minutes.',
};

export default function LandingPage() {
  return (
    <div className="theme-marketing min-h-screen bg-white text-[#111] font-sans"
         style={{ backgroundColor: 'white', color: '#111' }}>
      {/* ── Navbar ── */}
      <NavHeader />

      {/* ── Main ── */}
      <main>
        {/* 1. Hero */}
        <Hero />

        {/* 2. Problem */}
        <div id="problem">
          <ProblemSection />
        </div>

        {/* 3. Solution */}
        <SolutionSection />

        {/* 4. How it works (Workflow) */}
        <div id="workflow">
          <WorkflowPreview />
        </div>

        {/* 4.5. Product Flow Diagram */}
        <ProductFlowDiagram />

        {/* 5. Features Grid */}
        <div id="features">
          <Features />
        </div>

        {/* 6. Sample Output Preview */}
        <SamplePreview />

        {/* 7. Comparison */}
        <div id="compare">
          <ComparisonSection />
        </div>

        {/* 8. Tech Strip */}
        <TechStrip />

        {/* 9. Final CTA */}
        <CTABanner />
      </main>

      {/* ── Footer ── */}
      <footer className="border-t border-border-dim py-12 px-6 lg:px-12 bg-bg-surface">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-text-primary tracking-tight">Cirus</span>
            <span className="text-xs font-medium text-text-muted ml-2">Cloud Incident Intelligence</span>
          </div>
          <p className="text-xs text-text-faint">
            © {new Date().getFullYear()} Cirus. Built for SREs and platform engineers.
          </p>
        </div>
      </footer>
    </div>
  );
}
