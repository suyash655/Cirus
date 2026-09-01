import type {
  Incident,
  IncidentDetail,
  ArtifactSet,
  RCAArtifact,
  PolicyArtifact,
  IaCArtifact,
  AlertsArtifact,
  RunbookArtifact,
  RegressionArtifact,
  WorkflowRun,
  RiskScore,
  ExtractionResult,
  DashboardStats,
} from './types';

// ═══════════════════════════════════════════
// CIRUS — Realistic Mock Data
// ═══════════════════════════════════════════

// ─── Incident 1: S3 Public Exposure ──────────────────────────────────────────
const rca1: RCAArtifact = {
  type: 'rca',
  executiveSummary:
    'On 2024-03-14 at 02:17 UTC, an automated Terraform apply routine inadvertently set the `block_public_acls` flag to `false` on the production S3 bucket `prod-user-uploads-us-east-1`. This exposed approximately 47,000 user profile images and 1,200 PDF invoices to the public internet for 4 hours 23 minutes before detection via AWS Config conformance pack drift notification.',
  rootCause:
    `A junior engineer merged a Terraform variable override file (tfvars/prod-override.tfvars) that contained block_public_acls = false intended only for a local development sandbox. The CI pipeline Terraform plan output was not reviewed by a second approver because the CODEOWNERS file excluded .tfvars files from required review.`,
  contributingFactors: [
    'CODEOWNERS rule excluded `.tfvars` files from mandatory review',
    'No Sentinel policy enforced `block_public_acls = true` in CI',
    'AWS Config remediation was in "detect" mode, not "auto-remediate"',
    'No pre-apply diff review step in the CD pipeline',
    'S3 bucket ACL audit alert had a 4-hour evaluation window',
  ],
  impactAnalysis: {
    affectedSystems: ['prod-user-uploads-us-east-1', 'CDN (CloudFront)', 'Invoice Service'],
    userImpact:
      'Profile images were publicly accessible without authentication. Invoice PDFs containing partial billing addresses were potentially exposed. No database records, credentials, or PII beyond images/invoices were affected.',
    dataScopingNote:
      'CloudTrail S3 access logs show no evidence of mass enumeration or downloads during the exposure window. Investigation ongoing.',
    estimatedDuration: '4 hours 23 minutes (02:17 UTC – 06:40 UTC)',
  },
  timeline: [
    {
      id: 'tl-1',
      timestamp: '2024-03-14T02:17:00Z',
      title: 'Misconfiguration Applied',
      description: 'Terraform apply pipeline ran and set block_public_acls to false.',
      type: 'detection',
    },
    {
      id: 'tl-2',
      timestamp: '2024-03-14T02:19:00Z',
      title: 'S3 ACL Changed',
      description: 'AWS Config recorded the drift from conformance pack baseline.',
      type: 'impact',
    },
    {
      id: 'tl-3',
      timestamp: '2024-03-14T06:32:00Z',
      title: 'Alert Fired',
      description: 'AWS Config 4-hour evaluation window expired, SNS notification sent to security-alerts@.',
      type: 'detection',
    },
    {
      id: 'tl-4',
      timestamp: '2024-03-14T06:40:00Z',
      title: 'Mitigation Applied',
      description: 'On-call SRE ran emergency Terraform apply to re-enable block_public_acls.',
      type: 'mitigation',
    },
    {
      id: 'tl-5',
      timestamp: '2024-03-14T06:45:00Z',
      title: 'Incident Resolved',
      description: 'Bucket returned to private state. CloudFront cache invalidated.',
      type: 'resolution',
    },
  ],
  lessonsLearned: [
    'CODEOWNERS must cover all infrastructure-affecting file types including .tfvars',
    'Sentinel or OPA policies should enforce S3 security baselines in CI before apply',
    'AWS Config remediation should be in auto-remediate mode for critical controls',
    'CD pipelines must require a human approval step for any apply affecting storage ACLs',
  ],
  actionItems: [
    {
      id: 'ai-1',
      title: 'Update CODEOWNERS to include *.tfvars and *.tfvars.json',
      priority: 'high',
      owner: 'Platform Team',
      dueDate: '2024-03-21',
      status: 'open',
    },
    {
      id: 'ai-2',
      title: 'Write and deploy OPA/Rego policy: deny S3 block_public_acls=false',
      priority: 'high',
      owner: 'Security Team',
      dueDate: '2024-03-18',
      status: 'in-progress',
    },
    {
      id: 'ai-3',
      title: 'Enable AWS Config auto-remediation for S3 public access conformance pack',
      priority: 'medium',
      owner: 'Cloud Ops',
      dueDate: '2024-03-25',
      status: 'open',
    },
  ],
};

const policy1: PolicyArtifact = {
  type: 'policy',
  language: 'rego',
  description:
    'OPA/Rego policy that denies any Terraform plan that sets block_public_acls or block_public_policy to false on an aws_s3_bucket_public_access_block resource.',
  enforcement: 'deny',
  rationale:
    'This incident was caused by a Terraform variable override that disabled S3 public access blocking. This policy enforces that no S3 bucket in any environment can have public access controls weakened.',
  code: `package terraform.s3.public_access

import future.keywords.in

# Deny if any aws_s3_bucket_public_access_block resource disables blocking
deny[msg] {
  resource := input.resource_changes[_]
  resource.type == "aws_s3_bucket_public_access_block"
  
  after := resource.change.after
  
  # Check all four flags — all must be true
  flag_name := [
    "block_public_acls",
    "block_public_policy",
    "ignore_public_acls",
    "restrict_public_buckets",
  ][_]
  
  after[flag_name] == false
  
  msg := sprintf(
    "POLICY VIOLATION: S3 bucket public access block '%s' has '%s' set to false. All public access blocking flags must be true in production.",
    [resource.address, flag_name]
  )
}

# Also deny if the resource is being destroyed (removing protection)
deny[msg] {
  resource := input.resource_changes[_]
  resource.type == "aws_s3_bucket_public_access_block"
  resource.change.actions[_] == "delete"
  
  msg := sprintf(
    "POLICY VIOLATION: Destroying public access block resource '%s' is not permitted without security team approval.",
    [resource.address]
  )
}`,
  tests: `package terraform.s3.public_access_test

test_deny_block_public_acls_false {
  deny[_] with input as {
    "resource_changes": [{
      "address": "aws_s3_bucket_public_access_block.prod",
      "type": "aws_s3_bucket_public_access_block",
      "change": {
        "actions": ["update"],
        "after": {
          "block_public_acls": false,
          "block_public_policy": true,
          "ignore_public_acls": true,
          "restrict_public_buckets": true
        }
      }
    }]
  }
}

test_allow_all_true {
  count(deny) == 0 with input as {
    "resource_changes": [{
      "address": "aws_s3_bucket_public_access_block.prod",
      "type": "aws_s3_bucket_public_access_block",
      "change": {
        "actions": ["create"],
        "after": {
          "block_public_acls": true,
          "block_public_policy": true,
          "ignore_public_acls": true,
          "restrict_public_buckets": true
        }
      }
    }]
  }
}`,
};

const iac1: IaCArtifact = {
  type: 'iac',
  tool: 'terraform',
  description:
    'Terraform patch to harden the S3 public access block settings and enforce them via a Terraform variable with validation.',
  breakingChange: false,
  affectedResources: [
    'aws_s3_bucket_public_access_block.prod',
    'aws_s3_bucket.prod_uploads',
  ],
  diff: `--- a/modules/storage/main.tf
+++ b/modules/storage/main.tf
@@ -12,10 +12,18 @@ resource "aws_s3_bucket" "prod_uploads" {
   tags = local.common_tags
 }
 
-resource "aws_s3_bucket_public_access_block" "prod" {
-  bucket = aws_s3_bucket.prod_uploads.id
-
-  block_public_acls       = var.block_public_acls
-  block_public_policy     = var.block_public_policy
-  ignore_public_acls      = var.ignore_public_acls
-  restrict_public_buckets = var.restrict_public_buckets
-}
+resource "aws_s3_bucket_public_access_block" "prod" {
+  bucket = aws_s3_bucket.prod_uploads.id
+
+  # SECURITY: These must always be true. Never override via tfvars.
+  # Incident 2024-03-14: tfvars override caused 4h exposure window.
+  block_public_acls       = true
+  block_public_policy     = true
+  ignore_public_acls      = true
+  restrict_public_buckets = true
+}
+
+# Enforce bucket ownership to BucketOwnerEnforced (disables ACLs entirely)
+resource "aws_s3_bucket_ownership_controls" "prod" {
+  bucket = aws_s3_bucket.prod_uploads.id
+  rule {
+    object_ownership = "BucketOwnerEnforced"
+  }
+}
+
+# Block ACL-based public grants at the bucket policy level
+resource "aws_s3_bucket_policy" "prod_deny_public" {
+  bucket = aws_s3_bucket.prod_uploads.id
+  policy = jsonencode({
+    Version = "2012-10-17"
+    Statement = [{
+      Sid       = "DenyPublicRead"
+      Effect    = "Deny"
+      Principal = "*"
+      Action    = "s3:GetObject"
+      Resource  = "\${aws_s3_bucket.prod_uploads.arn}/*"
+      Condition = {
+        StringNotEquals = {
+          "aws:PrincipalArn" = [
+            "arn:aws:iam::\${data.aws_caller_identity.current.account_id}:root",
+          ]
+        }
+      }
+    }]
+  })
+}`,
  fullPatch: '',
};

const alerts1: AlertsArtifact = {
  type: 'alerts',
  provider: 'prometheus',
  description:
    'CloudWatch and Prometheus alert rules to detect S3 public access misconfigurations within 60 seconds instead of 4 hours.',
  rules: [
    {
      name: 'S3BucketPublicAccessEnabled',
      severity: 'critical',
      expression: 'aws_config_compliance_by_config_rule{rule_name="s3-bucket-public-access-blocked",compliance_type="NON_COMPLIANT"} > 0',
      duration: '1m',
      labels: { team: 'security', category: 'data-exposure', sev: 'P1' },
      annotations: {
        summary: 'S3 bucket has public access enabled',
        description: 'One or more S3 buckets have public access blocking disabled. Immediate remediation required. Check AWS Config for affected resources.',
        runbook_url: 'https://runbooks.internal/s3-public-access',
        dashboard: 'https://grafana.internal/d/s3-security',
      },
    },
    {
      name: 'TerraformApplyAffectedS3ACL',
      severity: 'warning',
      expression: 'rate(cloudtrail_events_total{event_name=~"PutBucketAcl|PutBucketPublicAccessBlock", resource_type="S3"}[5m]) > 0',
      duration: '0m',
      labels: { team: 'platform', category: 'config-change' },
      annotations: {
        summary: 'S3 ACL configuration was modified',
        description: 'A Terraform apply or manual action modified S3 ACL configuration. Verify the change was intentional and authorized.',
        runbook_url: 'https://runbooks.internal/s3-acl-change',
      },
    },
  ],
};

const runbook1: RunbookArtifact = {
  type: 'runbook',
  title: 'S3 Public Access Exposure — Incident Response Runbook',
  description:
    'Step-by-step guide for on-call engineers responding to an S3 public access exposure incident.',
  prerequisites: [
    'AWS CLI configured with read access to the affected account',
    'Terraform CLI and access to the infra repository',
    'PagerDuty escalation path for the Security team',
    'Access to Slack #security-incidents channel',
  ],
  steps: [
    {
      id: 1,
      title: 'Confirm the exposure',
      description: 'Verify which S3 buckets are currently publicly accessible using AWS CLI.',
      command: `aws s3api get-public-access-block --bucket <BUCKET_NAME>
# Expected: all flags should be "true"
# If any is "false" — proceed immediately to Step 2`,
      expectedOutput: `{\n  "PublicAccessBlockConfiguration": {\n    "BlockPublicAcls": false,\n    "IgnorePublicAcls": false,\n    "BlockPublicPolicy": false,\n    "RestrictPublicBuckets": false\n  }\n}`,
      note: 'Also check AWS Config dashboard for the full scope of affected buckets.',
    },
    {
      id: 2,
      title: 'Immediately block public access via CLI (emergency)',
      description: 'Do not wait for Terraform. Apply directly via CLI to stop the bleeding.',
      command: `aws s3api put-public-access-block \\
  --bucket <BUCKET_NAME> \\
  --public-access-block-configuration \\
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true`,
      severityGate: 'P1',
    },
    {
      id: 3,
      title: 'Identify the change source',
      description: 'Use CloudTrail to find who or what made the change.',
      command: `aws cloudtrail lookup-events \\
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutPublicAccessBlock \\
  --start-time $(date -d '8 hours ago' --iso-8601=seconds) \\
  --query 'Events[*].{Time:EventTime,User:Username,Source:SourceIPAddress}'`,
    },
    {
      id: 4,
      title: 'Check CloudFront cache for exposed objects',
      description: 'Invalidate the CDN cache to prevent stale public URLs from serving content.',
      command: `aws cloudfront create-invalidation \\
  --distribution-id <DISTRIBUTION_ID> \\
  --paths "/*"`,
    },
    {
      id: 5,
      title: 'Apply the Terraform fix',
      description: 'Apply the hardened Terraform configuration from the iac-patch artifact.',
      command: `# In your infra repository
git checkout -b fix/s3-public-access-incident-$(date +%Y%m%d)
# Apply the IaC patch from the Cirus artifact
terraform plan -var-file=prod.tfvars -target=aws_s3_bucket_public_access_block.prod
terraform apply -var-file=prod.tfvars -target=aws_s3_bucket_public_access_block.prod`,
    },
    {
      id: 6,
      title: 'Notify affected users and file security report',
      description: 'Post incident summary to #security-incidents. If PII was exposed, escalate to legal within 1 hour.',
      note: 'GDPR Article 33 requires notification to supervisory authority within 72 hours if PII exposure is confirmed.',
      severityGate: 'P1',
    },
  ],
  escalation: 'If you cannot remediate within 30 minutes, escalate to Security On-Call (PagerDuty: security-oncall) and notify the VP of Engineering.',
  references: [
    'https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html',
    'https://docs.aws.amazon.com/config/latest/developerguide/s3-bucket-public-access-prohibited.html',
  ],
};

const regression1: RegressionArtifact = {
  type: 'regression',
  framework: 'pytest',
  description:
    'Regression test suite to verify S3 public access blocking is correctly enforced across all production buckets.',
  testCases: [
    {
      id: 'rt-1',
      name: 'test_prod_bucket_has_public_access_blocked',
      description: 'Verify all production S3 buckets have all four public access block flags set to True.',
      category: 'positive',
      expectedResult: 'All four public access block flags are True for every bucket matching the prod- prefix.',
      code: `import boto3
import pytest

@pytest.fixture(scope="module")
def s3_client():
    return boto3.client("s3", region_name="us-east-1")

@pytest.fixture(scope="module")
def prod_buckets(s3_client):
    response = s3_client.list_buckets()
    return [b["Name"] for b in response["Buckets"] if b["Name"].startswith("prod-")]

def test_prod_bucket_has_public_access_blocked(s3_client, prod_buckets):
    assert prod_buckets, "No prod- buckets found — check AWS credentials"
    for bucket in prod_buckets:
        cfg = s3_client.get_public_access_block(Bucket=bucket)["PublicAccessBlockConfiguration"]
        assert cfg["BlockPublicAcls"], f"{bucket}: BlockPublicAcls is False"
        assert cfg["BlockPublicPolicy"], f"{bucket}: BlockPublicPolicy is False"
        assert cfg["IgnorePublicAcls"], f"{bucket}: IgnorePublicAcls is False"
        assert cfg["RestrictPublicBuckets"], f"{bucket}: RestrictPublicBuckets is False"`,
    },
    {
      id: 'rt-2',
      name: 'test_s3_object_not_publicly_accessible',
      description: 'Verify that uploading an object to the prod bucket does not make it publicly accessible.',
      category: 'negative',
      expectedResult: 'HTTP GET to the public S3 URL returns 403 Forbidden.',
      code: `import boto3
import requests
import uuid
import pytest

def test_s3_object_not_publicly_accessible():
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket = "prod-user-uploads-us-east-1"
    key = f"regression-test-{uuid.uuid4()}.txt"
    
    # Upload a test object
    s3.put_object(Bucket=bucket, Key=key, Body=b"regression test object")
    
    try:
        # Attempt to access it publicly
        public_url = f"https://{bucket}.s3.amazonaws.com/{key}"
        response = requests.get(public_url, timeout=5)
        assert response.status_code == 403, (
            f"Expected 403 Forbidden, got {response.status_code}. "
            f"S3 object may be publicly accessible!"
        )
    finally:
        s3.delete_object(Bucket=bucket, Key=key)`,
    },
    {
      id: 'rt-3',
      name: 'test_terraform_plan_denied_by_opa',
      description: 'Verify that a Terraform plan setting block_public_acls=false is denied by the OPA policy.',
      category: 'negative',
      expectedResult: 'OPA evaluation returns a non-empty deny set when block_public_acls is false.',
      code: `import json
import subprocess
import pytest

DENY_POLICY_PATH = "policies/s3_public_access.rego"

VIOLATING_PLAN = {
    "resource_changes": [{
        "address": "aws_s3_bucket_public_access_block.prod",
        "type": "aws_s3_bucket_public_access_block",
        "change": {
            "actions": ["update"],
            "after": {
                "block_public_acls": False,
                "block_public_policy": True,
                "ignore_public_acls": True,
                "restrict_public_buckets": True,
            }
        }
    }]
}

def test_terraform_plan_denied_by_opa():
    input_json = json.dumps({"input": VIOLATING_PLAN})
    result = subprocess.run(
        ["opa", "eval", "--data", DENY_POLICY_PATH, "--stdin-input",
         "data.terraform.s3.public_access.deny"],
        input=input_json, capture_output=True, text=True
    )
    output = json.loads(result.stdout)
    deny_set = output["result"][0]["expressions"][0]["value"]
    assert len(deny_set) > 0, "OPA policy should have denied this plan but did not!"`,
    },
  ],
};

// ─── Incidents List ───────────────────────────────────────────────────────────
export const MOCK_INCIDENTS: Incident[] = [
  {
    id: 'inc-001',
    title: 'S3 Bucket Public Access Inadvertently Enabled via Terraform Override',
    severity: 'P1',
    provider: 'AWS',
    status: 'ready',
    createdAt: '2024-03-14T06:50:00Z',
    updatedAt: '2024-03-14T07:12:00Z',
    summary:
      'A Terraform variable override set block_public_acls to false on the production S3 uploads bucket, exposing 47K files for 4h 23m.',
    tags: ['s3', 'terraform', 'public-exposure', 'acl'],
    artifactsReady: ['rca', 'policy', 'iac', 'alerts', 'runbook', 'regression'],
  },
  {
    id: 'inc-002',
    title: 'GKE Node Pool Auto-Upgrade Caused 18-Minute API Server Outage',
    severity: 'P2',
    provider: 'GCP',
    status: 'ready',
    createdAt: '2024-03-10T14:22:00Z',
    updatedAt: '2024-03-10T15:04:00Z',
    summary:
      'GKE auto-upgrade to 1.28 during peak traffic caused a rolling node pool restart that exceeded PodDisruptionBudget limits, causing API server unavailability.',
    tags: ['gke', 'kubernetes', 'upgrade', 'pod-disruption'],
    artifactsReady: ['rca', 'policy', 'iac', 'runbook'],
  },
  {
    id: 'inc-003',
    title: 'Azure SQL Database Failover Misconfiguration — Read Replica Served Stale Data',
    severity: 'P2',
    provider: 'Azure',
    status: 'partial',
    createdAt: '2024-03-08T09:15:00Z',
    updatedAt: '2024-03-08T10:30:00Z',
    summary:
      'Incorrect connection string routing sent 30% of read queries to a replica with a 45-minute replication lag, causing data inconsistency for reporting users.',
    tags: ['azure-sql', 'failover', 'replication', 'connection-string'],
    artifactsReady: ['rca', 'runbook'],
  },
  {
    id: 'inc-004',
    title: 'Lambda Cold Start Cascade — 5x Latency Spike on Product Search',
    severity: 'P3',
    provider: 'AWS',
    status: 'processing',
    createdAt: '2024-03-15T11:00:00Z',
    updatedAt: '2024-03-15T11:00:00Z',
    summary:
      'Provisioned concurrency was removed during a cost-optimization pass. A traffic spike caused cold starts to cascade, increasing p99 latency from 120ms to 680ms.',
    tags: ['lambda', 'cold-start', 'performance', 'concurrency'],
    artifactsReady: [],
  },
];

// ─── Incident Details ─────────────────────────────────────────────────────────
export const MOCK_INCIDENT_DETAILS: Record<string, IncidentDetail> = {
  'inc-001': {
    ...MOCK_INCIDENTS[0],
    rawText: `INCIDENT REPORT — P1 SEVERITY
Reported by: Security Monitoring System
Timestamp: 2024-03-14T06:32:00Z

Summary:
AWS Config conformance pack drift detection identified that the S3 bucket 
"prod-user-uploads-us-east-1" had public access blocking disabled.

Analysis showed that a Terraform apply at 02:17 UTC applied a variable 
override file (tfvars/prod-override.tfvars) containing:
  block_public_acls = false

This file was intended only for sandbox environments but was accidentally 
included in the production pipeline by a junior engineer whose PR was merged 
without review of the .tfvars file (CODEOWNERS excluded .tfvars from required review).

Impact: ~47,000 user profile images and ~1,200 invoice PDFs were publicly 
accessible for 4h 23m.`,
    detectedFormat: 'plain',
    timeline: rca1.timeline,
  },
};

// ─── Artifact Sets ────────────────────────────────────────────────────────────
export const MOCK_ARTIFACT_SETS: Record<string, ArtifactSet> = {
  'inc-001': {
    rca: rca1,
    policy: policy1,
    iac: iac1,
    alerts: alerts1,
    runbook: runbook1,
    regression: regression1,
  },
  'inc-002': {
    rca: {
      type: 'rca',
      executiveSummary:
        'GKE auto-upgrade to version 1.28 during peak traffic caused a rolling node pool restart that breached PodDisruptionBudget limits, resulting in 18 minutes of API server degradation affecting 23% of users.',
      rootCause:
        'The maintenance window for auto-upgrades was set to "any time" rather than a specific off-peak window. The upgrade was triggered at 14:22 UTC on a Tuesday, which overlaps with peak EU traffic hours.',
      contributingFactors: [
        'Auto-upgrade maintenance window not configured to off-peak hours',
        'PodDisruptionBudget was set to maxUnavailable: 1 but node pool had surge capacity of 0',
        'Kubernetes API server health check timeout was 30s, causing cascading readiness failures',
        'No canary or staged rollout for node pool upgrades',
      ],
      impactAnalysis: {
        affectedSystems: ['GKE Node Pool: prod-n2-standard-8', 'API Gateway', 'User Service'],
        userImpact: '23% of API requests returned 503 errors for 18 minutes during peak EU business hours.',
        dataScopingNote: 'No data loss occurred. All in-flight requests were retried successfully by client SDKs.',
        estimatedDuration: '18 minutes (14:22–14:40 UTC)',
      },
      timeline: [
        { id: 't1', timestamp: '2024-03-10T14:22:00Z', title: 'Auto-upgrade triggered', description: 'GKE initiated 1.27→1.28 node pool upgrade.', type: 'detection' },
        { id: 't2', timestamp: '2024-03-10T14:25:00Z', title: 'Pods evicted beyond PDB', description: 'Node drain exceeded PDB limits, causing pod unavailability.', type: 'impact' },
        { id: 't3', timestamp: '2024-03-10T14:35:00Z', title: 'Alert fired', description: 'SLO burn rate alert triggered on API error rate.', type: 'detection' },
        { id: 't4', timestamp: '2024-03-10T14:40:00Z', title: 'Upgrade completed', description: 'Node pool upgrade finished, pods rescheduled successfully.', type: 'resolution' },
      ],
      lessonsLearned: [
        'GKE auto-upgrade maintenance windows must be explicitly scoped to off-peak hours',
        'PodDisruptionBudgets must account for node pool surge settings',
        'Upgrade runbook must be tested in staging with production-equivalent load',
      ],
      actionItems: [
        { id: 'ai-1', title: 'Set GKE maintenance window to 00:00–04:00 UTC', priority: 'high', owner: 'Platform Team', dueDate: '2024-03-17', status: 'done' },
        { id: 'ai-2', title: 'Update PDB to use maxUnavailable: 10%', priority: 'medium', owner: 'Platform Team', dueDate: '2024-03-20', status: 'open' },
      ],
    },
    policy: {
      type: 'policy',
      language: 'rego',
      description: 'Sentinel policy to enforce GKE maintenance windows are configured for off-peak hours.',
      enforcement: 'warn',
      rationale: 'Enforce that all GKE node pools have explicit maintenance windows set to non-business hours.',
      code: `package gcp.gke.maintenance_window\n\ndeny[msg] {\n  resource := input.resource_changes[_]\n  resource.type == "google_container_node_pool"\n  not resource.change.after.management[_].auto_upgrade_start_time\n  msg := sprintf("GKE node pool '%s' has no explicit auto-upgrade maintenance window.", [resource.address])\n}`,
      tests: `# tests omitted for brevity`,
    },
    iac: {
      type: 'iac',
      tool: 'terraform',
      description: 'Terraform patch to add explicit maintenance windows and improve PodDisruptionBudget settings.',
      breakingChange: false,
      affectedResources: ['google_container_node_pool.prod'],
      diff: `--- a/gke/node_pool.tf\n+++ b/gke/node_pool.tf\n@@ -10,6 +10,14 @@ resource "google_container_node_pool" "prod" {\n   management {\n     auto_repair  = true\n-    auto_upgrade = true\n+    auto_upgrade = true\n+  }\n+\n+  # SECURITY: Restrict auto-upgrade to off-peak window\n+  upgrade_settings {\n+    max_surge       = 1\n+    max_unavailable = 0\n+  }\n+\n+  timeouts {\n+    create = "30m"\n+    update = "40m"\n   }\n }`,
      fullPatch: '',
    },
    runbook: runbook1,
  },
};

// ─── Workflow Runs ────────────────────────────────────────────────────────────

export const MOCK_WORKFLOW_RUNS: Record<string, WorkflowRun> = {
  'run-001': {
    id: 'run-001',
    incidentId: 'inc-001',
    status: 'completed',
    modelId: 'claude-3-7-sonnet',
    triggeredBy: 'manual',
    startedAt: '2024-03-14T07:00:00Z',
    updatedAt: '2024-03-14T07:01:38Z',
    completedAt: '2024-03-14T07:01:38Z',
    totalTokensUsed: 14320,
    stages: [
      {
        id: 'human-input',
        label: 'Human Input',
        description: 'User-provided incident report received and validated',
        status: 'completed',
        startedAt: '2024-03-14T07:00:00Z',
        completedAt: '2024-03-14T07:00:01Z',
        durationMs: 1200,
        output: {
          summary: 'Incident report received. Format: plain text. Length: 1,247 chars. Detected provider signals: AWS, S3.',
          tokensUsed: 340,
        },
        confidence: 1.0,
      },
      {
        id: 'normalization',
        label: 'Normalization',
        description: 'Structured extraction of incident fields from raw text',
        status: 'completed',
        startedAt: '2024-03-14T07:00:01Z',
        completedAt: '2024-03-14T07:00:09Z',
        durationMs: 8100,
        output: {
          summary: 'Extracted: provider=AWS, severity=P1, 4 affected services, timeline with 5 events, 3 error codes identified.',
          data: {
            provider: 'AWS',
            severity: 'P1',
            servicesCount: 4,
            timelineEvents: 5,
            errorCodes: ['AccessDenied', 'PublicACLChange', 'ConfigDrift'],
          },
          tokensUsed: 1820,
        },
        confidence: 0.96,
      },
      {
        id: 'root-cause-classification',
        label: 'Root Cause Classification',
        description: 'AI classifies the root cause from the normalized incident data',
        status: 'completed',
        startedAt: '2024-03-14T07:00:09Z',
        completedAt: '2024-03-14T07:00:27Z',
        durationMs: 18200,
        output: {
          summary: 'Root cause classified as: IaC misconfiguration → Terraform variable override. Category: Configuration Drift. Confidence: 0.94.',
          data: {
            category: 'Configuration Drift',
            subcategory: 'IaC Override',
            rootCauseStatement: 'Terraform .tfvars override file set block_public_acls=false outside of code review scope',
            confidence: 0.94,
          },
          warnings: ['Ambiguity detected between human error and process gap — classified as both'],
          tokensUsed: 3140,
        },
        confidence: 0.94,
      },
      {
        id: 'context-enrichment',
        label: 'Context Enrichment',
        description: 'Enriches with AWS service context, CVE data, and historical patterns',
        status: 'completed',
        startedAt: '2024-03-14T07:00:27Z',
        completedAt: '2024-03-14T07:00:41Z',
        durationMs: 14100,
        output: {
          summary: 'Enriched with: S3 public access documentation, 3 similar historical incidents from corpus, GDPR Article 33 compliance note, AWS Config rule reference.',
          data: {
            relatedDocs: 3,
            historicalMatches: 3,
            complianceFlags: ['GDPR-Art33', 'SOC2-CC6.1'],
            similarIncidents: ['inc-similar-001', 'inc-similar-002'],
          },
          tokensUsed: 2210,
        },
        confidence: 0.91,
      },
      {
        id: 'artifact-generation',
        label: 'Artifact Generation',
        description: 'Generates all 6 prevention artifacts in parallel',
        status: 'completed',
        startedAt: '2024-03-14T07:00:41Z',
        completedAt: '2024-03-14T07:01:22Z',
        durationMs: 41000,
        output: {
          summary: '6 artifacts generated: RCA (2,100 tokens), Policy/Rego (890 tokens), IaC Patch/Terraform (1,240 tokens), Alert Rules (560 tokens), Runbook (1,800 tokens), Regression Tests (1,400 tokens).',
          data: {
            artifactsGenerated: ['rca', 'policy', 'iac', 'alerts', 'runbook', 'regression'],
            totalArtifactTokens: 7990,
          },
          tokensUsed: 7990,
        },
        confidence: 0.92,
      },
      {
        id: 'validator-critic',
        label: 'Validator / Critic',
        description: 'Secondary model reviews artifacts for correctness and completeness',
        status: 'completed',
        startedAt: '2024-03-14T07:01:22Z',
        completedAt: '2024-03-14T07:01:35Z',
        durationMs: 13100,
        output: {
          summary: 'Validation passed. Minor improvement applied to Rego test coverage (+2 test cases). No hallucinations detected. IaC patch verified syntactically valid.',
          data: {
            issuesFound: 1,
            issuesResolved: 1,
            hallucintationsDetected: 0,
            syntaxValid: true,
          },
          warnings: ['Rego test coverage improved from 2 to 4 cases'],
          tokensUsed: 820,
        },
        confidence: 0.97,
      },
      {
        id: 'human-approval',
        label: 'Human Approval',
        description: 'Awaiting engineer review and approval of generated artifacts',
        status: 'completed',
        startedAt: '2024-03-14T07:01:35Z',
        completedAt: '2024-03-14T07:01:38Z',
        durationMs: 3000,
        output: {
          summary: 'Artifacts approved by on-call SRE. All 6 artifacts marked ready for deployment.',
          tokensUsed: 0,
        },
        confidence: 1.0,
      },
    ],
  },
  'run-002': {
    id: 'run-002',
    incidentId: 'inc-004',
    status: 'running',
    modelId: 'claude-3-7-sonnet',
    triggeredBy: 'auto',
    startedAt: new Date(Date.now() - 25000).toISOString(),
    updatedAt: new Date().toISOString(),
    totalTokensUsed: 5510,
    stages: [
      {
        id: 'human-input',
        label: 'Human Input',
        description: 'User-provided incident report received and validated',
        status: 'completed',
        startedAt: new Date(Date.now() - 25000).toISOString(),
        completedAt: new Date(Date.now() - 24000).toISOString(),
        durationMs: 900,
        output: { summary: 'Incident report received. Format: plain text.', tokensUsed: 290 },
        confidence: 1.0,
      },
      {
        id: 'normalization',
        label: 'Normalization',
        description: 'Structured extraction of incident fields from raw text',
        status: 'completed',
        startedAt: new Date(Date.now() - 24000).toISOString(),
        completedAt: new Date(Date.now() - 16000).toISOString(),
        durationMs: 8100,
        output: { summary: 'Extracted: provider=AWS, severity=P3, Lambda cold start pattern identified.', tokensUsed: 1820 },
        confidence: 0.93,
      },
      {
        id: 'root-cause-classification',
        label: 'Root Cause Classification',
        description: 'AI classifies the root cause from the normalized incident data',
        status: 'completed',
        startedAt: new Date(Date.now() - 16000).toISOString(),
        completedAt: new Date(Date.now() - 5000).toISOString(),
        durationMs: 11000,
        output: { summary: 'Root cause: Provisioned concurrency removed during cost-optimization. Confidence: 0.88.', tokensUsed: 3400 },
        confidence: 0.88,
      },
      {
        id: 'context-enrichment',
        label: 'Context Enrichment',
        description: 'Enriches with AWS service context and historical patterns',
        status: 'running',
        startedAt: new Date(Date.now() - 5000).toISOString(),
        tokensUsed: 0,
      },
      {
        id: 'artifact-generation',
        label: 'Artifact Generation',
        description: 'Generates all prevention artifacts in parallel',
        status: 'pending',
      },
      {
        id: 'validator-critic',
        label: 'Validator / Critic',
        description: 'Secondary model reviews artifacts for correctness',
        status: 'pending',
      },
      {
        id: 'human-approval',
        label: 'Human Approval',
        description: 'Awaiting engineer review and approval',
        status: 'pending',
      },
    ],
  },
};

// ─── Risk Scores ──────────────────────────────────────────────────────────────

export const MOCK_RISK_SCORES: Record<string, RiskScore> = {
  'inc-001': {
    overall: 87,
    beforeRemediation: 87,
    afterRemediation: 18,
    delta: 69,
    calculatedAt: '2024-03-14T07:01:00Z',
    dimensions: {
      exposure: {
        score: 95,
        label: 'Exposure',
        description: '47K files publicly accessible on the internet without auth',
      },
      blast_radius: {
        score: 72,
        label: 'Blast Radius',
        description: 'Production bucket with user PII, limited to images and invoices',
      },
      recurrence: {
        score: 88,
        label: 'Recurrence Risk',
        description: 'CODEOWNERS gap and no CI policy enforcement means this can recur',
      },
      remediation_effort: {
        score: 35,
        label: 'Remediation Effort',
        description: 'Single Terraform apply + CODEOWNERS update, low effort',
      },
    },
  },
  'inc-002': {
    overall: 64,
    beforeRemediation: 64,
    afterRemediation: 21,
    delta: 43,
    calculatedAt: '2024-03-10T15:00:00Z',
    dimensions: {
      exposure: {
        score: 45,
        label: 'Exposure',
        description: 'Service degradation visible to 23% of users, no data exposure',
      },
      blast_radius: {
        score: 78,
        label: 'Blast Radius',
        description: 'API server affecting multiple downstream consumers',
      },
      recurrence: {
        score: 82,
        label: 'Recurrence Risk',
        description: 'Maintenance window still unconfigured for other node pools',
      },
      remediation_effort: {
        score: 42,
        label: 'Remediation Effort',
        description: 'Terraform config + GKE console change required',
      },
    },
  },
};

// ─── Extraction Results ───────────────────────────────────────────────────────

export const MOCK_EXTRACTIONS: Record<string, ExtractionResult> = {
  'inc-001': {
    title: 'S3 Bucket Public Access Inadvertently Enabled via Terraform Override',
    detectedProvider: 'AWS',
    detectedSeverity: 'P1',
    affectedServices: ['Amazon S3', 'AWS CloudFront', 'AWS Config', 'Invoice Service'],
    timeRange: { start: '2024-03-14T02:17:00Z', end: '2024-03-14T06:40:00Z' },
    errorMessages: [
      'CONFIG-DRIFT: s3-bucket-public-access-prohibited NON_COMPLIANT',
      'S3 ACL modification detected on prod-user-uploads-us-east-1',
      'PutPublicAccessBlock called with BlockPublicAcls=false',
    ],
    structuredData: {
      bucketName: 'prod-user-uploads-us-east-1',
      exposedObjects: 48200,
      changeSource: 'Terraform CI pipeline',
      overrideFile: 'tfvars/prod-override.tfvars',
    },
    confidence: 0.94,
    citations: [
      {
        id: 'cit-1',
        text: 'block_public_acls = false intended only for a local development sandbox',
        source: 'incident-text',
        relevance: 0.97,
        lineNumber: 8,
      },
      {
        id: 'cit-2',
        text: 'CODEOWNERS file excluded .tfvars files from required review',
        source: 'incident-text',
        relevance: 0.93,
        lineNumber: 11,
      },
      {
        id: 'cit-3',
        text: 'AWS Config 4-hour evaluation window expired',
        source: 'config-drift',
        relevance: 0.88,
      },
    ],
  },
};

// ─── Dashboard Stats ──────────────────────────────────────────────────────────

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  totalIncidents: 3,
  guardrailsGenerated: 18,
  avgRiskReduction: 41,
  awaitingApproval: 1,
  mttgHours: 0.8,
  artifactSummary: {
    policies: 3,
    iacPatches: 3,
    alerts: 7,
    runbooks: 3,
    regressionTests: 9,
  },
  riskTrend: [
    { date: 'Feb 20', avgRiskBefore: 82, avgRiskAfter: 78 },
    { date: 'Feb 27', avgRiskBefore: 79, avgRiskAfter: 71 },
    { date: 'Mar 05', avgRiskBefore: 76, avgRiskAfter: 60 },
    { date: 'Mar 10', avgRiskBefore: 71, avgRiskAfter: 52 },
    { date: 'Mar 14', avgRiskBefore: 88, avgRiskAfter: 49 },  // S3 incident spike + fix
    { date: 'Mar 21', avgRiskBefore: 75, avgRiskAfter: 44 },  // Autoscaling incident
    { date: 'Mar 28', avgRiskBefore: 70, avgRiskAfter: 38 },
    { date: 'Apr 05', avgRiskBefore: 83, avgRiskAfter: 41 },  // DB pool incident
    { date: 'Apr 10', avgRiskBefore: 65, avgRiskAfter: 35 },
    { date: 'Apr 15', avgRiskBefore: 60, avgRiskAfter: 33 },
  ],
};


