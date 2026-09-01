'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, Shield, FileCode2, Bell, BookOpen } from 'lucide-react';
import { CodeBlock } from '@/components/ui/code-block';
import { Reveal } from './motion-primitives';

const SAMPLE_TABS = [
  { id: 'summary', label: 'Summary', icon: <span className="text-[10px]">📋</span> },
  { id: 'policy', label: 'Policy (OPA)', icon: <Shield className="w-3.5 h-3.5 text-text-muted group-hover:text-text-primary transition-colors" /> },
  { id: 'terraform', label: 'Terraform Patch', icon: <FileCode2 className="w-3.5 h-3.5 text-text-muted group-hover:text-text-primary transition-colors" /> },
  { id: 'alert', label: 'Alert Rule', icon: <Bell className="w-3.5 h-3.5 text-text-muted group-hover:text-text-primary transition-colors" /> },
  { id: 'runbook', label: 'Runbook', icon: <BookOpen className="w-3.5 h-3.5 text-text-muted group-hover:text-text-primary transition-colors" /> },
];

const SAMPLE_CODE = {
  policy: `package main

# Deny S3 public access overrides
deny[msg] {
    input.resource_type == "aws_s3_bucket_public_access_block"
    input.attributes.block_public_acls == false
    msg := "S3 bucket public ACLs must be blocked at all times"
}

deny[msg] {
    input.resource_type == "aws_s3_bucket_public_access_block"
    input.attributes.ignore_public_acls == false
    msg := "S3 bucket public ACLs must be ignored"
}`,
  terraform: `--- a/modules/storage/s3.tf
+++ b/modules/storage/s3.tf
@@ -12,4 +12,4 @@
 resource "aws_s3_bucket_public_access_block" "prod_uploads" {
   bucket = aws_s3_bucket.prod_uploads.id
-  block_public_acls       = false
-  ignore_public_acls      = false
+  block_public_acls       = true
+  ignore_public_acls      = true
   block_public_policy     = true
   restrict_public_buckets = true
 }`,
  alert: `- alert: S3PublicAccessBlockDisabled
  expr: aws_s3_bucket_public_access_block_status{block_public_acls="false"} == 1
  for: 1m
  labels:
    severity: critical
    team: platform
  annotations:
    summary: "Public access block disabled on S3 bucket {{ $labels.bucket }}"
    description: "S3 bucket {{ $labels.bucket }} has block_public_acls set to false. Immediate remediation required."
    runbook_url: "https://cirus.local/runbooks/rb-4091"`,
};

export function SamplePreview() {
  const [activeTab, setActiveTab] = useState('summary');

  return (
    <section className="py-24 lg:py-32 bg-bg-base relative overflow-hidden border-t border-border-dim">
      <div className="max-w-5xl mx-auto px-6 lg:px-12 flex flex-col items-center">
        <Reveal className="text-center mb-12 lg:mb-20">
          <span className="text-[11px] font-mono tracking-widest text-text-muted uppercase mb-4 block">
            Output Preview
          </span>
          <h2 className="text-3xl lg:text-4xl font-medium text-text-primary">
            Ready to merge. Ready to deploy.
          </h2>
        </Reveal>

        <Reveal delay={0.1} className="w-full rounded-2xl bg-bg-surface border border-border-strong overflow-hidden shadow-sm">
          {/* Header */}
          <div className="flex items-center gap-4 px-6 py-4 border-b border-border-dim bg-bg-base">
            <div className="flex gap-1.5">
              <span className="w-3 h-3 rounded-full border border-border-strong bg-bg-surface" />
              <span className="w-3 h-3 rounded-full border border-border-strong bg-bg-surface" />
              <span className="w-3 h-3 rounded-full border border-border-strong bg-bg-surface" />
            </div>
            <span className="text-xs font-mono text-text-secondary">incident-1049.outputs</span>
            <div className="ml-auto flex items-center gap-2">
              <span className="flex items-center text-[11px] font-medium text-text-secondary bg-bg-surface border border-border-dim px-2 py-0.5 rounded">
                <Check className="w-3 h-3 mr-1" /> All artifacts ready
              </span>
            </div>
          </div>

          <div className="flex flex-col md:flex-row min-h-[450px]">
            {/* Sidebar Tabs */}
            <div className="w-full md:w-56 border-b md:border-b-0 md:border-r border-border-dim bg-bg-base p-3 flex flex-row md:flex-col gap-1 overflow-x-auto">
              {SAMPLE_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className="group flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all text-left whitespace-nowrap outline-none focus-visible:ring-2 focus-visible:ring-text-primary"
                  style={{
                    background: activeTab === tab.id ? 'hsl(var(--bg-surface))' : 'transparent',
                    color: activeTab === tab.id ? 'hsl(var(--text-primary))' : 'hsl(var(--text-secondary))',
                    border: activeTab === tab.id ? '1px solid hsl(var(--border-dim))' : '1px solid transparent',
                  }}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Content Area */}
            <div className="flex-1 p-6 bg-bg-surface">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  {activeTab === 'summary' && (
                    <div className="flex flex-col gap-5 h-full">
                      <div className="p-6 rounded-xl border border-border-dim bg-bg-base">
                        <h4 className="text-[11px] font-bold uppercase tracking-widest text-text-primary mb-3">Executive Summary</h4>
                        <p className="text-[14px] text-text-secondary leading-relaxed">
                          A Terraform deployment overrode the S3 public access block on the prod-uploads bucket, exposing 47,000 files to the public internet for 43 minutes. The override bypassed manual code review.
                        </p>
                      </div>
                      <div className="p-6 rounded-xl border border-border-dim bg-bg-base">
                        <h4 className="text-[11px] font-bold uppercase tracking-widest text-text-primary mb-3">Action Items Generated</h4>
                        <ul className="flex flex-col gap-3">
                          <li className="text-[14px] text-text-secondary flex items-center gap-3"><Check className="w-4 h-4 text-text-primary" /> Apply Terraform patch to reinstate blocks</li>
                          <li className="text-[14px] text-text-secondary flex items-center gap-3"><Check className="w-4 h-4 text-text-primary" /> Merge OPA policy to CI/CD pipeline</li>
                          <li className="text-[14px] text-text-secondary flex items-center gap-3"><Check className="w-4 h-4 text-text-primary" /> Deploy CloudWatch alert rule</li>
                        </ul>
                      </div>
                    </div>
                  )}

                  {activeTab === 'policy' && (
                    <CodeBlock code={SAMPLE_CODE.policy} language="rego" filename="aws_s3_block.rego" />
                  )}

                  {activeTab === 'terraform' && (
                    <CodeBlock code={SAMPLE_CODE.terraform} language="diff" filename="s3.tf.patch" />
                  )}

                  {activeTab === 'alert' && (
                    <CodeBlock code={SAMPLE_CODE.alert} language="yaml" filename="prometheus-rules.yml" />
                  )}

                  {activeTab === 'runbook' && (
                    <div className="flex flex-col gap-4">
                      <p className="text-[14px] text-text-secondary mb-2">Runbook for handling disabled S3 public access blocks.</p>
                      <div className="p-5 rounded-xl border border-border-dim bg-bg-base">
                        <h5 className="text-[13px] font-semibold text-text-primary mb-3">1. Verify current status via AWS CLI</h5>
                        <CodeBlock code="aws s3api get-public-access-block --bucket prod-uploads" language="bash" showLineNumbers={false} />
                      </div>
                      <div className="p-5 rounded-xl border border-border-dim bg-bg-base">
                        <h5 className="text-[13px] font-semibold text-text-primary mb-3">2. Emergency Remediation Command</h5>
                        <CodeBlock code={`aws s3api put-public-access-block \\
    --bucket prod-uploads \\
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"`} language="bash" showLineNumbers={false} />
                      </div>
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
