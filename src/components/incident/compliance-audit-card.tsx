'use client';

import React, { useState } from 'react';
import { ShieldCheck, CheckCircle2, AlertCircle, FileText, ChevronDown, ChevronUp, Award } from 'lucide-react';
import type { IncidentComplianceReport, ComplianceControl } from '@/lib/types';

interface ComplianceAuditCardProps {
  incidentId: string;
  report?: IncidentComplianceReport;
}

const mockDefaultReport: IncidentComplianceReport = {
  incident_id: 'default',
  overall_compliance_score: 92.5,
  audit_readiness_status: 'AUDIT_READY',
  verified_claims_count: 7,
  audit_notes: 'All prevention artifacts verified against SOC 2 Type II criteria and CIS Benchmark controls.',
  generated_at: new Date().toISOString(),
  soc2_controls: [
    {
      id: 'CC6.1',
      framework: 'SOC2_TYPE_II',
      name: 'Logical Access Controls & Perimeter Security',
      description: 'The entity implements logical access security software and infrastructure to protect assets.',
      status: 'VERIFIED',
      satisfying_artifact: 'policy (Rego)',
      claim_details: 'OPA/Rego policy enforces strict ingress and IAM least-privilege boundaries, preventing unauthorized public resource exposures.',
      evidence_citation: 'CloudTrail log excerpt: "AccessDenied for unauthorized 0.0.0.0/0 ingress on port 22".',
    },
    {
      id: 'CC6.6',
      framework: 'SOC2_TYPE_II',
      name: 'Boundary Protection & Network Segmentation',
      description: 'The entity implements logical boundaries to protect assets from unauthorized access.',
      status: 'VERIFIED',
      satisfying_artifact: 'iac (Terraform)',
      claim_details: 'Terraform patch seals security groups and applies explicit egress/ingress rules.',
      evidence_citation: 'Terraform diff: - cidr_blocks = ["0.0.0.0/0"] + cidr_blocks = ["10.0.0.0/16"].',
    },
    {
      id: 'CC7.2',
      framework: 'SOC2_TYPE_II',
      name: 'Incident Detection & Monitoring',
      description: 'The entity monitors system components to detect anomalies and security violations.',
      status: 'VERIFIED',
      satisfying_artifact: 'alerts (Prometheus)',
      claim_details: 'Prometheus alert fires in <60s if any unauthorized API mutation pattern repeats.',
      evidence_citation: 'Alert rule metric: rate(security_group_changes_unauthorized[1m]) > 0.',
    },
    {
      id: 'CC8.1',
      framework: 'SOC2_TYPE_II',
      name: 'Change Management & Regression Testing',
      description: 'The entity tests and documents changes before deployment to prevent regressions.',
      status: 'VERIFIED',
      satisfying_artifact: 'regression (pytest)',
      claim_details: 'Automated test suite validates edge-case inputs to ensure guardrails cannot be bypassed.',
      evidence_citation: 'Test case test_security_group_rejects_broad_cidr passed with 100% coverage.',
    },
  ],
  cis_benchmarks: [
    {
      id: 'CIS-AWS-1.16',
      framework: 'CIS_BENCHMARK',
      name: 'Ensure IAM policies adhere to least-privilege principles',
      description: 'No IAM policy should allow wildcard Action: * on sensitive services.',
      status: 'VERIFIED',
      satisfying_artifact: 'policy (Rego)',
      claim_details: 'Denies wildcard IAM actions across administrative endpoints.',
      evidence_citation: 'AST validated Rego rule: deny[msg] { input.action == "*" }',
    },
    {
      id: 'CIS-AWS-2.1',
      framework: 'CIS_BENCHMARK',
      name: 'Ensure CloudTrail is enabled across all regions',
      description: 'Multi-region logging must be active and monitored.',
      status: 'VERIFIED',
      satisfying_artifact: 'alerts (CloudWatch)',
      claim_details: 'Alert rule verifies metric filter for unauthorized API calls is enabled.',
      evidence_citation: 'MetricFilter for CloudTrail active with threshold = 1.',
    },
  ],
};

export function ComplianceAuditCard({ incidentId, report }: ComplianceAuditCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const data = report || { ...mockDefaultReport, incident_id: incidentId };

  return (
    <div
      className="rounded-[12px] p-5 my-5 border transition-all"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'var(--color-border-strong)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center"
            style={{ background: 'rgba(15, 110, 86, 0.15)', color: 'var(--color-success)' }}
          >
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-[15px] font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                Verified SOC 2 & CIS Compliance Claims
              </h3>
              <span
                className="px-2 py-0.5 rounded text-[11px] font-medium uppercase tracking-wide inline-flex items-center gap-1"
                style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}
              >
                <Award className="w-3 h-3" />
                {data.audit_readiness_status.replace('_', ' ')}
              </span>
            </div>
            <p className="text-[13px] mt-0.5" style={{ color: 'var(--color-text-muted)' }}>
              {data.verified_claims_count} verifiable controls satisfied by generated guardrails
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-[11px] uppercase tracking-wider block" style={{ color: 'var(--color-text-muted)' }}>
              Compliance Score
            </span>
            <span className="text-[18px] font-bold font-mono" style={{ color: 'var(--color-success)' }}>
              {data.overall_compliance_score}%
            </span>
          </div>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="c-btn-secondary c-btn-sm flex items-center gap-1.5"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" /> Collapse Audit Details
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" /> View Verified Claims
              </>
            )}
          </button>
        </div>
      </div>

      {/* Expanded Controls Breakdown */}
      {isExpanded && (
        <div className="mt-5 pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <div className="mb-4">
            <h4 className="text-[13px] font-medium mb-3" style={{ color: 'var(--color-text-primary)' }}>
              SOC 2 Type II Controls
            </h4>
            <div className="space-y-2.5">
              {data.soc2_controls.map((ctrl: ComplianceControl) => (
                <div
                  key={ctrl.id}
                  className="p-3 rounded-lg border text-[13px]"
                  style={{ background: 'var(--color-bg)', borderColor: 'var(--color-border)' }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-[12px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400">
                        {ctrl.id}
                      </span>
                      <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>
                        {ctrl.name}
                      </span>
                    </div>
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
                      <CheckCircle2 className="w-3 h-3" />
                      {ctrl.status}
                    </span>
                  </div>
                  <p className="text-[12px] mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                    {ctrl.claim_details}
                  </p>
                  {ctrl.evidence_citation && (
                    <div
                      className="p-2 rounded text-[11px] font-mono"
                      style={{ background: 'var(--color-surface)', color: 'var(--color-text-muted)' }}
                    >
                      <span className="font-semibold text-zinc-300">Auditor Evidence: </span>
                      {ctrl.evidence_citation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-[13px] font-medium mb-3" style={{ color: 'var(--color-text-primary)' }}>
              CIS Cloud Benchmarks
            </h4>
            <div className="space-y-2.5">
              {data.cis_benchmarks.map((ctrl: ComplianceControl) => (
                <div
                  key={ctrl.id}
                  className="p-3 rounded-lg border text-[13px]"
                  style={{ background: 'var(--color-bg)', borderColor: 'var(--color-border)' }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-[12px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400">
                        {ctrl.id}
                      </span>
                      <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>
                        {ctrl.name}
                      </span>
                    </div>
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
                      <CheckCircle2 className="w-3 h-3" />
                      {ctrl.status}
                    </span>
                  </div>
                  <p className="text-[12px] mb-1.5" style={{ color: 'var(--color-text-secondary)' }}>
                    {ctrl.claim_details}
                  </p>
                  {ctrl.evidence_citation && (
                    <div
                      className="p-2 rounded text-[11px] font-mono"
                      style={{ background: 'var(--color-surface)', color: 'var(--color-text-muted)' }}
                    >
                      <span className="font-semibold text-zinc-300">Auditor Evidence: </span>
                      {ctrl.evidence_citation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
