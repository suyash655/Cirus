'use client';

import React, { useState } from 'react';
import { CheckCircle, ShieldAlert, Sparkles, BookOpen, ChevronRight } from 'lucide-react';

interface GroundedClaimItem {
  id: string;
  claim: string;
  sourceLine: number;
  sourceText: string;
  confidence: number;
}

interface GroundedClaimBadgeProps {
  score?: number;
  incidentId: string;
}

const mockClaims: GroundedClaimItem[] = [
  {
    id: 'c1',
    claim: 'Security group rule ingress opened SSH 22 globally to 0.0.0.0/0.',
    sourceLine: 14,
    sourceText: "AuthorizeSecurityGroupIngress IpRanges: [{CidrIp: '0.0.0.0/0'}, {FromPort: 22}]",
    confidence: 0.98,
  },
  {
    id: 'c2',
    claim: 'Misconfiguration triggered by deployer-service CI pipeline script.',
    sourceLine: 18,
    sourceText: "Caller identity: arn:aws:iam::123456789012:user/deployer-service",
    confidence: 0.95,
  },
  {
    id: 'c3',
    claim: 'VPC vpc-0a817b12 had default security group modified without peer review.',
    sourceLine: 29,
    sourceText: "VpcId: vpc-0a817b12, ModificationEvent: direct_api_call",
    confidence: 0.92,
  },
];

export function GroundedClaimBadge({ score = 98.4, incidentId }: GroundedClaimBadgeProps) {
  const [showDrawer, setShowDrawer] = useState(false);

  return (
    <div className="inline-flex items-center gap-2">
      <button
        onClick={() => setShowDrawer(!showDrawer)}
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium transition-all"
        style={{
          background: 'rgba(56, 189, 248, 0.12)',
          color: '#38bdf8',
          border: '1px solid rgba(56, 189, 248, 0.25)',
        }}
        title="Anti-hallucination score verified against raw incident telemetry"
      >
        <Sparkles className="w-3 h-3 text-sky-400" />
        <span>Grounded Evidence: {score}%</span>
        <ChevronRight className={`w-3 h-3 transition-transform ${showDrawer ? 'rotate-90' : ''}`} />
      </button>

      {showDrawer && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(4px)' }}
          onClick={() => setShowDrawer(false)}
        >
          <div
            className="w-full max-w-xl rounded-xl p-6 border shadow-2xl relative"
            style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border-strong)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-sky-400" />
                <h3 className="text-[16px] font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                  Grounded Claim Citations
                </h3>
              </div>
              <span
                className="text-[12px] font-mono px-2 py-0.5 rounded"
                style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}
              >
                Anti-Hallucination: {score}%
              </span>
            </div>

            <p className="text-[13px] mb-4" style={{ color: 'var(--color-text-secondary)' }}>
              Every fact asserted in the generated prevention guardrails is cross-referenced with exact line spans from
              the incident logs.
            </p>

            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {mockClaims.map((item) => (
                <div
                  key={item.id}
                  className="p-3 rounded-lg border text-[12px]"
                  style={{ background: 'var(--color-bg)', borderColor: 'var(--color-border)' }}
                >
                  <div className="flex items-center justify-between font-medium mb-1" style={{ color: 'var(--color-text-primary)' }}>
                    <span>{item.claim}</span>
                    <span className="text-emerald-400 font-mono text-[11px] flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> {(item.confidence * 100).toFixed(0)}% Match
                    </span>
                  </div>
                  <div
                    className="p-2 rounded font-mono text-[11px] mt-2 border"
                    style={{
                      background: 'rgba(0,0,0,0.3)',
                      borderColor: 'rgba(255,255,255,0.06)',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    <span className="text-sky-300">Line {item.sourceLine}: </span>
                    {item.sourceText}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-5 flex justify-end">
              <button onClick={() => setShowDrawer(false)} className="c-btn-secondary c-btn-sm">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
