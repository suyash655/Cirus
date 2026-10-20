#!/usr/bin/env python
"""CIRUS — Demo Incidents Seeder.

Seeds 3 realistic production incidents into the CIRUS database:
  1. AWS S3 Bucket Open to Public (Public Storage Leak)
  2. AWS Security Group Open to 0.0.0.0/0 on Port 22 (SSH Internet Exposure)
  3. Unencrypted RDS PostgreSQL Database Volume (Compliance Violation)

Each incident includes:
  - Incident details (title, severity, provider, status)
  - Completed WorkflowRun with 7 stage metadata
  - Authoritative Rego policy (cirus.guardrail) that prevents repeat
  - Terraform HCL remediation patch
  - Rego unit tests verifying deny on misconfiguration and allow on fix
  - Detailed RCA, Runbook, and Alerting rules

Usage:
  python backend/scripts/demo_incidents.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal
from app.db.base import Base
from app.db.session import engine
from app.models.incident import Incident, Severity, CloudProvider, IncidentStatus
from app.models.run import WorkflowRun, WorkflowRunStatus
from app.models.artifact import Artifact, ArtifactType
from app.models.citation import Citation
from sqlalchemy import select, delete


DEMO_INCIDENTS = [
    {
        "id": "inc-demo-001-s3",
        "title": "AWS S3 Bucket 'customer-exports-prod' Made Publicly Accessible",
        "summary": "Block Public Access was disabled on customer-exports-prod following a Terraform module update, allowing unauthorized downloads of customer data archives.",
        "raw_text": (
            "2024-04-10 14:02 UTC CRITICAL — AWS S3 bucket 'customer-exports-prod' had its Block Public Access "
            "settings disabled following an automated Terraform deployment. At 14:18 UTC, external monitoring "
            "detected unauthenticated GET requests downloading customer export archives (42 GB). "
            "Root cause: terraform module update removed aws_s3_bucket_public_access_block resource. "
            "Account: 123456789012. Region: us-east-1. Services affected: customer-exports-prod, data-pipeline."
        ),
        "severity": Severity.P1,
        "provider": CloudProvider.AWS,
        "tags": ["s3", "data-leak", "public-access", "terraform"],
        "policy_code": """package cirus.guardrail.s3

import rego.v1

default allow := false

# Deny any S3 bucket that has public access block disabled or missing
deny contains msg if {
    some resource in input.resources
    resource.type == "aws_s3_bucket"
    not resource.public_access_block
    msg := sprintf("S3 bucket '%v' must have public access block configured", [resource.name])
}

allow if {
    count(deny) == 0
}
""",
        "iac_code": """resource "aws_s3_bucket_public_access_block" "customer_exports_block" {
  bucket                  = "customer-exports-prod"
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
""",
        "test_code": """package cirus.guardrail.s3_test

import rego.v1
import data.cirus.guardrail.s3

test_public_s3_denied if {
    input := {"resources": [{"name": "customer-exports-prod", "type": "aws_s3_bucket", "public_access_block": false}]}
    count(s3.deny) > 0
}

test_private_s3_allowed if {
    input := {"resources": [{"name": "customer-exports-prod", "type": "aws_s3_bucket", "public_access_block": true}]}
    s3.allow
}
""",
        "rca": {
            "executiveSummary": "S3 bucket customer-exports-prod was unintentionally made public after a Terraform refactor removed the public access block resource.",
            "rootCause": "The public access block resource was omitted during a shared Terraform module migration.",
            "impact": "42 GB of customer export archives exposed to public internet for 48 minutes.",
            "timeline": [
                {"time": "14:02 UTC", "event": "Terraform deployment applied removing public access block"},
                {"time": "14:18 UTC", "event": "Anomalous external GET requests detected by CloudWatch"},
                {"time": "14:50 UTC", "event": "Public access block reapplied via emergency change"}
            ]
        },
        "runbook": {
            "title": "Public S3 Bucket Incident Remediation Runbook",
            "steps": [
                {"step": 1, "action": "Enable S3 Block Public Access immediately via AWS CLI or Terraform."},
                {"step": 2, "action": "Audit CloudTrail S3 server access logs for accessed object keys."},
                {"step": 3, "action": "Rotate all customer export API tokens and notify security incident command."}
            ]
        },
        "alerts": {
            "rules": [
                {
                    "alert": "S3PublicAccessBlockDisabled",
                    "expr": "aws_s3_public_access_block_status{bucket='customer-exports-prod'} == 0",
                    "severity": "critical",
                    "description": "Public access block has been removed from a production S3 bucket."
                }
            ]
        }
    },
    {
        "id": "inc-demo-002-firewall",
        "title": "AWS Security Group Ingress Rule Exposed SSH (Port 22) to 0.0.0.0/0",
        "summary": "Security group sg-0a91f4b2 was modified to allow ingress on port 22 from 0.0.0.0/0, leading to repeated brute-force authentication attempts against bastion hosts.",
        "raw_text": (
            "2024-05-02 03:15 UTC HIGH — SecOps IDS alerted that security group sg-0a91f4b2 was modified to allow "
            "inbound SSH traffic on port 22 from 0.0.0.0/0 (all internet). Within 10 minutes, over 12,000 automated "
            "brute-force login attempts were logged against internal bastion host ec2-bastion-prod. "
            "Root cause: On-call engineer temporarily allowed 0.0.0.0/0 during midnight troubleshooting and forgot to remove rule. "
            "Duration: 42 minutes. Account: 123456789012. Region: us-west-2."
        ),
        "severity": Severity.P1,
        "provider": CloudProvider.AWS,
        "tags": ["security-group", "firewall", "port-22", "ssh", "network"],
        "policy_code": """package cirus.guardrail.network

import rego.v1

default allow := false

# Deny any security group ingress allowing 0.0.0.0/0 on SSH port 22
deny contains msg if {
    some rule in input.ingress_rules
    rule.cidr == "0.0.0.0/0"
    rule.from_port <= 22
    rule.to_port >= 22
    msg := sprintf("Security group rule exposes SSH (port 22) to 0.0.0.0/0", [])
}

allow if {
    count(deny) == 0
}
""",
        "iac_code": """resource "aws_security_group_rule" "bastion_ssh_restricted" {
  type              = "ingress"
  from_port         = 22
  to_port           = 22
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/16"]
  security_group_id = "sg-0a91f4b2"
  description       = "Restrict SSH access to corporate VPN only"
}
""",
        "test_code": """package cirus.guardrail.network_test

import rego.v1
import data.cirus.guardrail.network

test_open_ssh_denied if {
    input := {"ingress_rules": [{"cidr": "0.0.0.0/0", "from_port": 22, "to_port": 22}]}
    count(network.deny) > 0
}

test_internal_ssh_allowed if {
    input := {"ingress_rules": [{"cidr": "10.0.0.0/16", "from_port": 22, "to_port": 22}]}
    network.allow
}
""",
        "rca": {
            "executiveSummary": "Ingress rule on port 22 with 0.0.0.0/0 opened SSH port to the internet, triggering brute-force attacks.",
            "rootCause": "Manual security group edit bypassed Infrastructure as Code pipeline during emergency debugging.",
            "impact": "12,000+ unauthorized connection attempts; zero successful logins verified.",
            "timeline": [
                {"time": "03:15 UTC", "event": "Ingress rule added allowing 0.0.0.0/0:22"},
                {"time": "03:25 UTC", "event": "IDS alert triggered by high connection rate"},
                {"time": "03:57 UTC", "event": "Rule replaced with restricted 10.0.0.0/16 VPN range"}
            ]
        },
        "runbook": {
            "title": "Open Port 22 Security Group Remediation Runbook",
            "steps": [
                {"step": 1, "action": "Revoke 0.0.0.0/0 ingress rule immediately using aws ec2 revoke-security-group-ingress."},
                {"step": 2, "action": "Apply Terraform security group rule with corporate CIDR block."},
                {"step": 3, "action": "Inspect SSH auth.log on bastion hosts for accepted keys."}
            ]
        },
        "alerts": {
            "rules": [
                {
                    "alert": "SecurityGroupOpenSSH",
                    "expr": "aws_security_group_open_port_22_count > 0",
                    "severity": "critical",
                    "description": "A security group allows port 22 ingress from 0.0.0.0/0."
                }
            ]
        }
    },
    {
        "id": "inc-demo-003-db",
        "title": "Unencrypted RDS PostgreSQL Database Volume Deployed in Production",
        "summary": "Database 'payments-db-primary' was provisioned without KMS encryption (storage_encrypted = false), violating PCI-DSS requirement 3.4.",
        "raw_text": (
            "2024-06-18 09:30 UTC MEDIUM — Compliance scan flagged RDS instance 'payments-db-primary' provisioned "
            "with storage_encrypted = false. The database hosts customer payment transaction references and "
            "operated without volume-level AES-256 encryption for 14 days. "
            "Root cause: Development Terraform variable default (storage_encrypted = false) was promoted to production environment. "
            "Account: 123456789012. Region: eu-central-1. Database: PostgreSQL 15.3."
        ),
        "severity": Severity.P2,
        "provider": CloudProvider.AWS,
        "tags": ["rds", "encryption", "kms", "compliance", "pci-dss"],
        "policy_code": """package cirus.guardrail.storage

import rego.v1

default allow := false

# Deny any database instance where storage encryption is disabled
deny contains msg if {
    some db in input.databases
    db.type == "aws_db_instance"
    not db.storage_encrypted
    msg := sprintf("Database '%v' must have storage encryption enabled", [db.name])
}

allow if {
    count(deny) == 0
}
""",
        "iac_code": """resource "aws_db_instance" "payments_db_encrypted" {
  identifier        = "payments-db-primary"
  engine            = "postgres"
  instance_class    = "db.t4g.medium"
  storage_encrypted = true
  kms_key_id        = "arn:aws:kms:eu-central-1:123456789012:key/payments-db-key"
}
""",
        "test_code": """package cirus.guardrail.storage_test

import rego.v1
import data.cirus.guardrail.storage

test_unencrypted_db_denied if {
    input := {"databases": [{"name": "payments-db-primary", "type": "aws_db_instance", "storage_encrypted": false}]}
    count(storage.deny) > 0
}

test_encrypted_db_allowed if {
    input := {"databases": [{"name": "payments-db-primary", "type": "aws_db_instance", "storage_encrypted": true}]}
    storage.allow
}
""",
        "rca": {
            "executiveSummary": "Production RDS instance was created without KMS storage encryption due to an inheritance flaw in environment variable flags.",
            "rootCause": "Terraform module defaulted storage_encrypted to false for local dev and lacked an environment override for production.",
            "impact": "PCI-DSS 3.4 non-compliance for 14 days. No disk data exfiltration observed.",
            "timeline": [
                {"time": "Day 0", "event": "Database provisioned without encryption"},
                {"time": "Day 14", "event": "Quarterly PCI-DSS compliance scan detected unencrypted volume"},
                {"time": "Day 14 + 4h", "event": "Encrypted snapshot created and cutover planned"}
            ]
        },
        "runbook": {
            "title": "Remediate Unencrypted RDS Database Runbook",
            "steps": [
                {"step": 1, "action": "Take an RDS manual snapshot of the unencrypted instance."},
                {"step": 2, "action": "Copy snapshot with KMS encryption key arn:aws:kms:..."},
                {"step": 3, "action": "Restore encrypted snapshot as new primary and swing DNS CNAME record."}
            ]
        },
        "alerts": {
            "rules": [
                {
                    "alert": "UnencryptedRDSInstanceFound",
                    "expr": "aws_rds_storage_encrypted == 0",
                    "severity": "high",
                    "description": "An RDS database was created without storage encryption."
                }
            ]
        }
    }
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for inc_data in DEMO_INCIDENTS:
            inc_id = inc_data["id"]

            # Remove existing demo incident if re-running
            existing = await session.execute(select(Incident).where(Incident.id == inc_id))
            if existing.scalar_one_or_none():
                await session.execute(delete(Artifact).where(Artifact.incident_id == inc_id))
                await session.execute(delete(WorkflowRun).where(WorkflowRun.incident_id == inc_id))
                await session.execute(delete(Incident).where(Incident.id == inc_id))
                await session.commit()

            # 1. Create Incident
            incident = Incident(
                id=inc_id,
                title=inc_data["title"],
                summary=inc_data["summary"],
                raw_text=inc_data["raw_text"],
                detected_format="plain",
                severity=inc_data["severity"],
                provider=inc_data["provider"],
                status=IncidentStatus.ready,
                tags=json.dumps(inc_data["tags"]),
                artifacts_ready=json.dumps(["policy", "iac", "regression", "rca", "runbook", "alerts"]),
            )
            session.add(incident)

            # 2. Create WorkflowRun
            run_id = f"run-{inc_id}"
            stages = [
                {"id": "normalization", "name": "Normalization", "status": "completed", "duration_ms": 120},
                {"id": "root_cause", "name": "Root Cause Analysis", "status": "completed", "duration_ms": 230},
                {"id": "context_enrichment", "name": "Context Enrichment", "status": "completed", "duration_ms": 95},
                {"id": "artifact_generation", "name": "Artifact Generation", "status": "completed", "duration_ms": 480},
                {"id": "validator_critic", "name": "Validator / Critic", "status": "completed", "duration_ms": 110},
                {"id": "risk_scoring", "name": "Risk Scoring", "status": "completed", "duration_ms": 50},
                {"id": "citation_extraction", "name": "Citation Extraction", "status": "completed", "duration_ms": 80},
            ]
            run = WorkflowRun(
                id=run_id,
                incident_id=inc_id,
                status=WorkflowRunStatus.completed,
                current_stage="completed",
                stages=json.dumps(stages),
                model_id="cirus-demo-engine",
                triggered_by="demo_seed",
                total_tokens_used=1250,
            )
            session.add(run)

            # 3. Create Artifacts
            artifacts = [
                (ArtifactType.policy, {"code": inc_data["policy_code"]}),
                (ArtifactType.iac, {"full_patch": inc_data["iac_code"], "fullPatch": inc_data["iac_code"]}),
                (ArtifactType.regression, {"test_code": inc_data["test_code"], "code": inc_data["test_code"]}),
                (ArtifactType.rca, inc_data["rca"]),
                (ArtifactType.runbook, inc_data["runbook"]),
                (ArtifactType.alerts, inc_data["alerts"]),
            ]

            for art_type, content in artifacts:
                art = Artifact(
                    id=f"art-{inc_id}-{art_type.value}",
                    incident_id=inc_id,
                    artifact_type=art_type,
                    content=json.dumps(content),
                    version=1,
                    model_id="cirus-demo-engine",
                    tokens_used=200,
                )
                session.add(art)

            await session.commit()
            print(f"[OK] Seeded demo incident: {inc_id} ({inc_data['title'][:40]}...)")

    print("\nSuccessfully seeded 3 demo incidents with complete artifacts and verification tests!")


if __name__ == "__main__":
    asyncio.run(seed())
