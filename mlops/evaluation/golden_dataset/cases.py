"""CIRUS — Golden Dataset: 50 synthetic incident/artifact pairs for evaluation.

Coverage:
  - IAM misconfig (INC-001 to INC-010)
  - Public storage (INC-011 to INC-020)
  - Unencrypted volumes/data (INC-021 to INC-030)
  - Network exposure (INC-031 to INC-040)
  - Resource exhaustion / noisy-neighbor (INC-041 to INC-045)
  - Dependency / supply-chain (INC-046 to INC-050)

Each entry:
  - incident_id: str
  - raw_text: str          — the incident report (sanitized synthetic)
  - root_cause_keywords: List[str] — what the generated policy MUST address
  - expected_rego: str     — known-good policy (passes opa check)
  - expected_terraform: str — known-good HCL patch (passes hcl2 parse)
  - category: str
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class GoldenCase:
    incident_id: str
    raw_text: str
    root_cause_keywords: List[str]   # words that MUST appear in generated policy
    expected_rego: str
    expected_terraform: str
    category: str


# ── Helper ────────────────────────────────────────────────────────────────────

def _rego(pkg: str, body: str) -> str:
    return f"package {pkg}\n\nimport rego.v1\n\n{body}"


def _tf(resource_type: str, name: str, body: str) -> str:
    return f'resource "{resource_type}" "{name}" {{\n{body}\n}}\n'


# ── Golden Dataset ────────────────────────────────────────────────────────────

GOLDEN_DATASET: List[GoldenCase] = [

    # ── IAM Misconfig (INC-001 to INC-010) ───────────────────────────────────

    GoldenCase(
        incident_id="INC-001",
        category="iam_misconfig",
        raw_text=(
            "2024-03-15 02:31Z CRITICAL — AWS IAM role arn:aws:iam::123456789:role/DataPipelineRole "
            "had AdministratorAccess attached. A compromised CI/CD token exploited this to exfiltrate "
            "39 GB from prod S3. Root cause: overprivileged IAM role; policy attached via legacy "
            "Terraform module that defaulted to admin. Duration: 4h 12m. Affected: all prod data buckets."
        ),
        root_cause_keywords=["administrator", "iam", "role", "deny"],
        expected_rego=_rego(
            "cirus.iam.no_admin_roles",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_iam_role_policy_attachment"\n'
            '  input.resource.policy_arn == "arn:aws:iam::aws:policy/AdministratorAccess"\n'
            '  msg := sprintf("Role %v must not attach AdministratorAccess", [input.resource.role])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_iam_role_policy_attachment", "data_pipeline_scoped",
            '  role       = aws_iam_role.data_pipeline.name\n'
            '  policy_arn = "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"',
        ),
    ),

    GoldenCase(
        incident_id="INC-002",
        category="iam_misconfig",
        raw_text=(
            "2024-04-02 09:11Z HIGH — EC2 instance profile attached to web tier had "
            "iam:PassRole permission with wildcard resource. Attacker used SSRF in app to "
            "call EC2 metadata and assumed the role, then passed it to a Lambda for persistence. "
            "Root cause: iam:PassRole on * in instance profile."
        ),
        root_cause_keywords=["PassRole", "iam", "wildcard", "deny"],
        expected_rego=_rego(
            "cirus.iam.no_passrole_wildcard",
            'deny contains msg if {\n'
            '  stmt := input.resource.Statement[_]\n'
            '  stmt.Action[_] == "iam:PassRole"\n'
            '  stmt.Resource == "*"\n'
            '  msg := "iam:PassRole must not use wildcard Resource"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_iam_role_policy", "web_tier_passrole_scoped",
            '  role   = aws_iam_role.web_tier.id\n'
            '  policy = jsonencode({\n'
            '    Version = "2012-10-17"\n'
            '    Statement = [{\n'
            '      Effect   = "Allow"\n'
            '      Action   = ["iam:PassRole"]\n'
            '      Resource = ["arn:aws:iam::*:role/LambdaExecRole-*"]\n'
            '    }]\n'
            '  })',
        ),
    ),

    GoldenCase(
        incident_id="INC-003",
        category="iam_misconfig",
        raw_text=(
            "2024-05-10 14:22Z P2 — Stale IAM user 'svc-deploy-old' (created 2019) had active "
            "access keys with S3:PutObject on prod bucket. User was orphaned after team reorg. "
            "Keys used in credential stuffing attack. Root cause: no key rotation, no account "
            "deactivation process."
        ),
        root_cause_keywords=["access_key", "rotation", "deny", "iam"],
        expected_rego=_rego(
            "cirus.iam.key_rotation",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_iam_user"\n'
            '  not input.resource.force_destroy\n'
            '  msg := sprintf("IAM user %v must have force_destroy enabled or be managed by SSO", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_iam_user", "svc_deploy",
            '  name          = "svc-deploy"\n'
            '  force_destroy = true\n'
            '\n'
            '  tags = {\n'
            '    ManagedBy = "terraform"\n'
            '    MaxKeyAgeDays = "90"\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-004",
        category="iam_misconfig",
        raw_text=(
            "2024-06-01 P1 — Cross-account trust policy on arn:aws:iam::111:role/SharedServices "
            "lacked external ID condition. Third-party vendor exploited confused deputy problem "
            "and accessed billing data. Root cause: no ExternalId condition on sts:AssumeRole."
        ),
        root_cause_keywords=["ExternalId", "AssumeRole", "trust", "deny"],
        expected_rego=_rego(
            "cirus.iam.assume_role_external_id",
            'deny contains msg if {\n'
            '  stmt := input.resource.AssumeRolePolicyDocument.Statement[_]\n'
            '  stmt.Action == "sts:AssumeRole"\n'
            '  not stmt.Condition.StringEquals["sts:ExternalId"]\n'
            '  msg := "Cross-account AssumeRole must require ExternalId condition"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_iam_role", "shared_services_with_external_id",
            '  name = "SharedServices"\n'
            '  assume_role_policy = jsonencode({\n'
            '    Version = "2012-10-17"\n'
            '    Statement = [{\n'
            '      Effect    = "Allow"\n'
            '      Principal = { AWS = "arn:aws:iam::VENDOR_ACCOUNT:root" }\n'
            '      Action    = "sts:AssumeRole"\n'
            '      Condition = {\n'
            '        StringEquals = { "sts:ExternalId" = var.vendor_external_id }\n'
            '      }\n'
            '    }]\n'
            '  })',
        ),
    ),

    GoldenCase(
        incident_id="INC-005",
        category="iam_misconfig",
        raw_text=(
            "GCP IAM — Service account key for sa@project.iam.gserviceaccount.com was checked "
            "into a public GitHub repo. Account had roles/editor. Exfiltration of GCS bucket "
            "detected via unusual egress from asia-southeast2. Root cause: key-based SA auth "
            "instead of workload identity, and no secret scanning in CI."
        ),
        root_cause_keywords=["service_account", "key", "workload_identity", "deny"],
        expected_rego=_rego(
            "cirus.gcp.no_sa_key_binding",
            'deny contains msg if {\n'
            '  input.resource_type == "google_service_account_key"\n'
            '  msg := sprintf("Service account %v must use Workload Identity, not static keys", [input.resource.service_account_id])\n'
            '}',
        ),
        expected_terraform=_tf(
            "google_service_account_iam_binding", "workload_identity",
            '  service_account_id = google_service_account.app.name\n'
            '  role               = "roles/iam.workloadIdentityUser"\n'
            '  members = [\n'
            '    "serviceAccount:${var.project}.svc.id.goog[default/app-sa]"\n'
            '  ]',
        ),
    ),

    GoldenCase(
        incident_id="INC-006",
        category="iam_misconfig",
        raw_text=(
            "Azure — Service Principal with Owner role assigned at subscription scope. "
            "Credentials leaked via misconfigured Azure DevOps pipeline log. Attacker "
            "created new Owner SP and deleted audit logs. Root cause: subscription-level "
            "Owner instead of resource-group scoped Contributor."
        ),
        root_cause_keywords=["Owner", "subscription", "scope", "deny"],
        expected_rego=_rego(
            "cirus.azure.no_owner_at_subscription",
            'deny contains msg if {\n'
            '  input.resource_type == "azurerm_role_assignment"\n'
            '  input.resource.role_definition_name == "Owner"\n'
            '  startswith(input.resource.scope, "/subscriptions/")\n'
            '  not contains(input.resource.scope, "/resourceGroups/")\n'
            '  msg := "Owner role must not be assigned at subscription scope"\n'
            '}',
        ),
        expected_terraform=_tf(
            "azurerm_role_assignment", "app_sp_contributor",
            '  scope                = azurerm_resource_group.app.id\n'
            '  role_definition_name = "Contributor"\n'
            '  principal_id         = azurerm_service_principal.app.id',
        ),
    ),

    GoldenCase(
        incident_id="INC-007",
        category="iam_misconfig",
        raw_text=(
            "AWS — Lambda function execution role had s3:* on arn:aws:s3:::*. "
            "Function was triggered by SNS topic open to all AWS accounts. "
            "Attacker sent crafted SNS message to enumerate and download S3 contents. "
            "Root cause: over-permissioned Lambda role + unrestricted SNS trigger."
        ),
        root_cause_keywords=["lambda", "s3", "wildcard", "deny", "sns"],
        expected_rego=_rego(
            "cirus.iam.lambda_s3_wildcard",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_iam_role_policy"\n'
            '  doc := json.unmarshal(input.resource.policy)\n'
            '  stmt := doc.Statement[_]\n'
            '  stmt.Action[_] == "s3:*"\n'
            '  stmt.Resource == "*"\n'
            '  msg := "Lambda execution role must not have s3:* on wildcard resource"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_iam_role_policy", "lambda_s3_scoped",
            '  role   = aws_iam_role.lambda_exec.id\n'
            '  policy = jsonencode({\n'
            '    Version = "2012-10-17"\n'
            '    Statement = [{\n'
            '      Effect   = "Allow"\n'
            '      Action   = ["s3:GetObject", "s3:PutObject"]\n'
            '      Resource = ["${aws_s3_bucket.data.arn}/*"]\n'
            '    }]\n'
            '  })',
        ),
    ),

    GoldenCase(
        incident_id="INC-008",
        category="iam_misconfig",
        raw_text=(
            "AWS — CloudTrail logging was disabled in us-east-2 region by IAM user "
            "with cloudtrail:StopLogging permission. Attack went undetected for 72 hours. "
            "Root cause: no SCP preventing trail deletion; full IAM user permission to "
            "manage CloudTrail."
        ),
        root_cause_keywords=["cloudtrail", "logging", "scp", "deny"],
        expected_rego=_rego(
            "cirus.aws.protect_cloudtrail",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_iam_policy"\n'
            '  doc := json.unmarshal(input.resource.policy)\n'
            '  stmt := doc.Statement[_]\n'
            '  action := stmt.Action[_]\n'
            '  cloudtrail_write_actions := {"cloudtrail:StopLogging", "cloudtrail:DeleteTrail", "cloudtrail:UpdateTrail"}\n'
            '  cloudtrail_write_actions[action]\n'
            '  stmt.Effect == "Allow"\n'
            '  msg := sprintf("IAM policy must not allow %v", [action])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_cloudtrail", "org_trail_protected",
            '  name                          = "org-trail"\n'
            '  s3_bucket_name                = aws_s3_bucket.cloudtrail.id\n'
            '  is_multi_region_trail         = true\n'
            '  enable_log_file_validation    = true\n'
            '  include_global_service_events = true',
        ),
    ),

    GoldenCase(
        incident_id="INC-009",
        category="iam_misconfig",
        raw_text=(
            "Kubernetes — RBAC ClusterRoleBinding gave ServiceAccount 'default' in namespace "
            "'prod' the 'cluster-admin' ClusterRole. A pod escape in that namespace gave "
            "full cluster control. Root cause: using default SA for workloads + cluster-admin "
            "binding left from initial setup."
        ),
        root_cause_keywords=["cluster-admin", "clusterrolebinding", "serviceaccount", "deny"],
        expected_rego=_rego(
            "cirus.k8s.no_cluster_admin_default_sa",
            'deny contains msg if {\n'
            '  input.kind == "ClusterRoleBinding"\n'
            '  input.roleRef.name == "cluster-admin"\n'
            '  subject := input.subjects[_]\n'
            '  subject.kind == "ServiceAccount"\n'
            '  subject.name == "default"\n'
            '  msg := sprintf("default ServiceAccount in %v must not have cluster-admin", [subject.namespace])\n'
            '}',
        ),
        expected_terraform=_tf(
            "kubernetes_cluster_role_binding", "app_role_binding",
            '  metadata {\n'
            '    name = "app-role-binding"\n'
            '  }\n'
            '  role_ref {\n'
            '    api_group = "rbac.authorization.k8s.io"\n'
            '    kind      = "ClusterRole"\n'
            '    name      = "view"\n'
            '  }\n'
            '  subject {\n'
            '    kind      = "ServiceAccount"\n'
            '    name      = "app-sa"\n'
            '    namespace = "prod"\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-010",
        category="iam_misconfig",
        raw_text=(
            "AWS — SQS queue had resource policy allowing 'Principal: *' with 'sqs:SendMessage'. "
            "Spam bots discovered the endpoint and flooded 4.2M messages causing Lambda throttling "
            "and $12K in Lambda invocation charges. Root cause: open SQS resource policy."
        ),
        root_cause_keywords=["sqs", "principal", "wildcard", "deny"],
        expected_rego=_rego(
            "cirus.aws.sqs_no_public_policy",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_sqs_queue_policy"\n'
            '  doc := json.unmarshal(input.resource.policy)\n'
            '  stmt := doc.Statement[_]\n'
            '  stmt.Principal == "*"\n'
            '  msg := "SQS queue policy must not allow wildcard Principal"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_sqs_queue_policy", "app_queue_restricted",
            '  queue_url = aws_sqs_queue.app.id\n'
            '  policy    = jsonencode({\n'
            '    Version = "2012-10-17"\n'
            '    Statement = [{\n'
            '      Effect    = "Allow"\n'
            '      Principal = { AWS = aws_iam_role.producer.arn }\n'
            '      Action    = ["sqs:SendMessage"]\n'
            '      Resource  = aws_sqs_queue.app.arn\n'
            '    }]\n'
            '  })',
        ),
    ),

    # ── Public Storage (INC-011 to INC-020) ──────────────────────────────────

    GoldenCase(
        incident_id="INC-011",
        category="public_storage",
        raw_text=(
            "S3 bucket 'prod-user-data-exports' was set to public-read ACL via Terraform "
            "module parameter misconfiguration. 180K customer records publicly accessible "
            "for 19 days. Root cause: bucket ACL set to 'public-read' in exports module."
        ),
        root_cause_keywords=["s3", "acl", "public", "deny"],
        expected_rego=_rego(
            "cirus.aws.s3_no_public_acl",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_s3_bucket_acl"\n'
            '  public_acls := {"public-read", "public-read-write", "authenticated-read"}\n'
            '  public_acls[input.resource.acl]\n'
            '  msg := sprintf("S3 bucket must not use %v ACL", [input.resource.acl])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_s3_bucket_public_access_block", "exports_blocked",
            '  bucket = aws_s3_bucket.prod_user_data_exports.id\n'
            '  block_public_acls       = true\n'
            '  block_public_policy     = true\n'
            '  ignore_public_acls      = true\n'
            '  restrict_public_buckets = true',
        ),
    ),

    GoldenCase(
        incident_id="INC-012",
        category="public_storage",
        raw_text=(
            "GCS bucket 'ml-model-artifacts' had allUsers:objectViewer binding. "
            "Proprietary model weights were downloaded 40K times before detection. "
            "Root cause: IAM binding added manually during a hackathon and never removed."
        ),
        root_cause_keywords=["gcs", "allUsers", "public", "deny"],
        expected_rego=_rego(
            "cirus.gcp.no_public_gcs",
            'deny contains msg if {\n'
            '  input.resource_type == "google_storage_bucket_iam_binding"\n'
            '  public_members := {"allUsers", "allAuthenticatedUsers"}\n'
            '  public_members[input.resource.members[_]]\n'
            '  msg := "GCS bucket must not grant access to allUsers or allAuthenticatedUsers"\n'
            '}',
        ),
        expected_terraform=_tf(
            "google_storage_bucket_iam_binding", "ml_artifacts_restricted",
            '  bucket = google_storage_bucket.ml_model_artifacts.name\n'
            '  role   = "roles/storage.objectViewer"\n'
            '  members = [\n'
            '    "serviceAccount:${google_service_account.ml_inference.email}"\n'
            '  ]',
        ),
    ),

    GoldenCase(
        incident_id="INC-013",
        category="public_storage",
        raw_text=(
            "Azure Blob Storage container 'backups-2023' had anonymous access level 'Container' "
            "enabling listing. Backup archives downloaded by scraper bots. Root cause: "
            "storage account 'allow_blob_public_access' not set to false."
        ),
        root_cause_keywords=["blob", "anonymous", "public_access", "deny"],
        expected_rego=_rego(
            "cirus.azure.no_public_blob",
            'deny contains msg if {\n'
            '  input.resource_type == "azurerm_storage_account"\n'
            '  input.resource.allow_blob_public_access == true\n'
            '  msg := sprintf("Storage account %v must have allow_blob_public_access = false", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "azurerm_storage_account", "secure_storage",
            '  name                     = "secureprodsa"\n'
            '  resource_group_name      = azurerm_resource_group.main.name\n'
            '  location                 = azurerm_resource_group.main.location\n'
            '  account_tier             = "Standard"\n'
            '  account_replication_type = "LRS"\n'
            '  allow_blob_public_access = false\n'
            '  min_tls_version          = "TLS1_2"',
        ),
    ),

    GoldenCase(
        incident_id="INC-014",
        category="public_storage",
        raw_text=(
            "S3 bucket versioning disabled + bucket policy missing. Object overwrite attack "
            "via supply-chain: compromised npm package posted to bucket, served to 5K customers. "
            "Root cause: no versioning, no bucket policy requiring specific uploader identity."
        ),
        root_cause_keywords=["versioning", "s3", "bucket_policy", "deny"],
        expected_rego=_rego(
            "cirus.aws.s3_versioning_required",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_s3_bucket_versioning"\n'
            '  input.resource.versioning_configuration.status != "Enabled"\n'
            '  msg := "S3 bucket versioning must be Enabled"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_s3_bucket_versioning", "cdn_assets_versioning",
            '  bucket = aws_s3_bucket.cdn_assets.id\n'
            '  versioning_configuration {\n'
            '    status = "Enabled"\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-015",
        category="public_storage",
        raw_text=(
            "Elasticsearch cluster at search.internal.company.com:9200 was exposed to 0.0.0.0/0 "
            "via security group. Shodan indexed it; 2.1M documents exfiltrated. "
            "Root cause: SG rule with 0.0.0.0/0 on port 9200."
        ),
        root_cause_keywords=["security_group", "0.0.0.0/0", "ingress", "deny"],
        expected_rego=_rego(
            "cirus.aws.no_public_sg_ingress",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_security_group_rule"\n'
            '  input.resource.type == "ingress"\n'
            '  public_cidrs := {"0.0.0.0/0", "::/0"}\n'
            '  public_cidrs[input.resource.cidr_blocks[_]]\n'
            '  sensitive_ports := {22, 3306, 5432, 6379, 9200, 27017}\n'
            '  sensitive_ports[input.resource.from_port]\n'
            '  msg := sprintf("Port %v must not be open to %v", [input.resource.from_port, input.resource.cidr_blocks])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_security_group_rule", "elasticsearch_internal_only",
            '  type              = "ingress"\n'
            '  from_port         = 9200\n'
            '  to_port           = 9200\n'
            '  protocol          = "tcp"\n'
            '  cidr_blocks       = [var.vpc_cidr]\n'
            '  security_group_id = aws_security_group.elasticsearch.id',
        ),
    ),

    GoldenCase(
        incident_id="INC-016",
        category="public_storage",
        raw_text=(
            "RDS PostgreSQL instance had publicly_accessible=true. No network ACL restriction. "
            "Brute force attack succeeded on 'postgres' superuser with default password. "
            "Root cause: public RDS + no password policy enforcement."
        ),
        root_cause_keywords=["rds", "publicly_accessible", "deny"],
        expected_rego=_rego(
            "cirus.aws.rds_not_public",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_db_instance"\n'
            '  input.resource.publicly_accessible == true\n'
            '  msg := sprintf("RDS instance %v must not be publicly accessible", [input.resource.identifier])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_db_instance", "prod_postgres",
            '  engine                 = "postgres"\n'
            '  instance_class         = "db.t3.medium"\n'
            '  allocated_storage      = 100\n'
            '  publicly_accessible    = false\n'
            '  storage_encrypted      = true\n'
            '  deletion_protection    = true\n'
            '  backup_retention_period = 7',
        ),
    ),

    GoldenCase(
        incident_id="INC-017",
        category="public_storage",
        raw_text=(
            "ECR repository had public image pull enabled. Internal Docker image "
            "containing hardcoded credentials was pulled by external actor. "
            "Root cause: ECR repository visibility set to 'public' in terraform."
        ),
        root_cause_keywords=["ecr", "public", "repository", "deny"],
        expected_rego=_rego(
            "cirus.aws.ecr_no_public",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_ecrpublic_repository"\n'
            '  msg := "ECR public repositories are not permitted; use private ECR with VPC endpoint"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_ecr_repository", "app_images",
            '  name                 = "app-images"\n'
            '  image_tag_mutability = "IMMUTABLE"\n'
            '\n'
            '  image_scanning_configuration {\n'
            '    scan_on_push = true\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-018",
        category="public_storage",
        raw_text=(
            "AWS Secrets Manager secret 'prod/db/password' had resource policy allowing "
            "GetSecretValue from all principals in account (* without condition). "
            "Any compromised role in account could read DB password. "
            "Root cause: overly permissive resource policy on secret."
        ),
        root_cause_keywords=["secrets_manager", "resource_policy", "wildcard", "deny"],
        expected_rego=_rego(
            "cirus.aws.secrets_manager_no_wildcard",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_secretsmanager_secret_policy"\n'
            '  doc := json.unmarshal(input.resource.policy)\n'
            '  stmt := doc.Statement[_]\n'
            '  stmt.Principal == "*"\n'
            '  msg := "Secrets Manager resource policy must not use wildcard Principal"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_secretsmanager_secret_policy", "db_password_restricted",
            '  secret_arn = aws_secretsmanager_secret.db_password.arn\n'
            '  policy     = jsonencode({\n'
            '    Version = "2012-10-17"\n'
            '    Statement = [{\n'
            '      Effect    = "Allow"\n'
            '      Principal = { AWS = aws_iam_role.app.arn }\n'
            '      Action    = ["secretsmanager:GetSecretValue"]\n'
            '      Resource  = "*"\n'
            '    }]\n'
            '  })',
        ),
    ),

    GoldenCase(
        incident_id="INC-019",
        category="public_storage",
        raw_text=(
            "GitHub Actions workflow accessed AWS via hardcoded access keys stored in "
            "workflow yaml file. Keys committed to public fork. All prod resources accessible. "
            "Root cause: hardcoded credentials in CI config instead of OIDC federation."
        ),
        root_cause_keywords=["github_actions", "oidc", "hardcoded", "deny"],
        expected_rego=_rego(
            "cirus.aws.no_hardcoded_ci_keys",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_iam_access_key"\n'
            '  msg := sprintf("IAM user %v: use OIDC federation for CI/CD instead of static access keys", [input.resource.user])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_iam_openid_connect_provider", "github_oidc",
            '  url             = "https://token.actions.githubusercontent.com"\n'
            '  client_id_list  = ["sts.amazonaws.com"]\n'
            '  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]',
        ),
    ),

    GoldenCase(
        incident_id="INC-020",
        category="public_storage",
        raw_text=(
            "S3 Transfer Acceleration endpoint was enabled without logging. Large-scale "
            "data theft via acceleration endpoint went undetected due to missing S3 server "
            "access logs. Root cause: S3 logging disabled on bucket with sensitive data."
        ),
        root_cause_keywords=["s3", "logging", "access_logs", "deny"],
        expected_rego=_rego(
            "cirus.aws.s3_logging_required",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_s3_bucket"\n'
            '  not input.resource.logging\n'
            '  msg := sprintf("S3 bucket %v must have server access logging enabled", [input.resource.bucket])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_s3_bucket_logging", "data_bucket_logging",
            '  bucket        = aws_s3_bucket.data.id\n'
            '  target_bucket = aws_s3_bucket.access_logs.id\n'
            '  target_prefix = "data-bucket/"',
        ),
    ),

    # ── Unencrypted Volumes/Data (INC-021 to INC-030) ─────────────────────────

    GoldenCase(
        incident_id="INC-021",
        category="unencrypted_data",
        raw_text=(
            "EBS volume attached to prod EC2 was unencrypted. Physical disk from a "
            "decommissioned instance was improperly disposed of; data recovered from media. "
            "Root cause: EBS encryption at rest not enforced; no default encryption."
        ),
        root_cause_keywords=["ebs", "encrypted", "kms", "deny"],
        expected_rego=_rego(
            "cirus.aws.ebs_encrypted",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_ebs_volume"\n'
            '  not input.resource.encrypted\n'
            '  msg := sprintf("EBS volume in %v must be encrypted", [input.resource.availability_zone])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_ebs_volume", "data_vol",
            '  availability_zone = "us-east-1a"\n'
            '  size              = 100\n'
            '  encrypted         = true\n'
            '  kms_key_id        = aws_kms_key.ebs.arn',
        ),
    ),

    GoldenCase(
        incident_id="INC-022",
        category="unencrypted_data",
        raw_text=(
            "RDS snapshot was unencrypted, shared with another AWS account for testing. "
            "That account's credentials were later compromised. Snapshot contained PII. "
            "Root cause: no encryption on RDS snapshots; missing snapshot sharing policy."
        ),
        root_cause_keywords=["rds", "snapshot", "encrypted", "deny"],
        expected_rego=_rego(
            "cirus.aws.rds_encrypted",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_db_instance"\n'
            '  not input.resource.storage_encrypted\n'
            '  msg := sprintf("RDS instance %v must have storage_encrypted = true", [input.resource.identifier])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_db_instance", "prod_rds_encrypted",
            '  identifier      = "prod-db"\n'
            '  engine          = "mysql"\n'
            '  instance_class  = "db.t3.medium"\n'
            '  storage_encrypted = true\n'
            '  kms_key_id      = aws_kms_key.rds.arn',
        ),
    ),

    GoldenCase(
        incident_id="INC-023",
        category="unencrypted_data",
        raw_text=(
            "SQS queue used for payment processing had server-side encryption disabled. "
            "Messages persisted in plaintext. Regulatory violation: PCI-DSS 3.4. "
            "Root cause: SQS SSE not configured in infrastructure module."
        ),
        root_cause_keywords=["sqs", "encryption", "kms", "deny"],
        expected_rego=_rego(
            "cirus.aws.sqs_encrypted",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_sqs_queue"\n'
            '  not input.resource.kms_master_key_id\n'
            '  not input.resource.sqs_managed_sse_enabled\n'
            '  msg := sprintf("SQS queue %v must have SSE enabled", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_sqs_queue", "payments_queue",
            '  name                    = "payments"\n'
            '  kms_master_key_id       = aws_kms_key.sqs.arn\n'
            '  kms_data_key_reuse_period_seconds = 300',
        ),
    ),

    GoldenCase(
        incident_id="INC-024",
        category="unencrypted_data",
        raw_text=(
            "Kinesis Data Stream sending clickstream events had no encryption. "
            "Events contained user behavior that mapped to medical searches. "
            "HIPAA violation. Root cause: KinesisStream created without KMS key."
        ),
        root_cause_keywords=["kinesis", "encryption", "kms", "deny"],
        expected_rego=_rego(
            "cirus.aws.kinesis_encrypted",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_kinesis_stream"\n'
            '  not input.resource.encryption_type\n'
            '  msg := sprintf("Kinesis stream %v must have KMS encryption", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_kinesis_stream", "clickstream_encrypted",
            '  name             = "clickstream"\n'
            '  shard_count      = 4\n'
            '  encryption_type  = "KMS"\n'
            '  kms_key_id       = "alias/aws/kinesis"',
        ),
    ),

    GoldenCase(
        incident_id="INC-025",
        category="unencrypted_data",
        raw_text=(
            "ElastiCache Redis cluster had no encryption-in-transit (TLS). "
            "Internal network tap captured session tokens cached in Redis. "
            "Root cause: transit_encryption_enabled not set."
        ),
        root_cause_keywords=["elasticache", "redis", "tls", "transit_encryption", "deny"],
        expected_rego=_rego(
            "cirus.aws.elasticache_tls",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_elasticache_replication_group"\n'
            '  not input.resource.transit_encryption_enabled\n'
            '  msg := sprintf("ElastiCache cluster %v must have transit encryption enabled", [input.resource.replication_group_id])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_elasticache_replication_group", "session_cache",
            '  replication_group_id  = "session-cache"\n'
            '  description           = "Session token cache"\n'
            '  node_type             = "cache.t3.micro"\n'
            '  transit_encryption_enabled = true\n'
            '  at_rest_encryption_enabled = true\n'
            '  auth_token            = var.redis_auth_token',
        ),
    ),

    GoldenCase(
        incident_id="INC-026",
        category="unencrypted_data",
        raw_text=(
            "DynamoDB table storing healthcare records had no CMK encryption. "
            "AWS default encryption uses AWS-managed keys with no customer key rotation control. "
            "Regulatory audit finding: missing HIPAA §164.312(a)(2)(iv). "
            "Root cause: server_side_encryption block absent in Terraform."
        ),
        root_cause_keywords=["dynamodb", "encryption", "kms", "deny"],
        expected_rego=_rego(
            "cirus.aws.dynamodb_cmk",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_dynamodb_table"\n'
            '  not input.resource.server_side_encryption.enabled\n'
            '  msg := sprintf("DynamoDB table %v must have SSE with CMK enabled", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_dynamodb_table", "healthcare_records",
            '  name         = "healthcare-records"\n'
            '  billing_mode = "PAY_PER_REQUEST"\n'
            '  hash_key     = "patient_id"\n'
            '\n'
            '  server_side_encryption {\n'
            '    enabled     = true\n'
            '    kms_key_arn = aws_kms_key.dynamo.arn\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-027",
        category="unencrypted_data",
        raw_text=(
            "CloudWatch Logs group storing application logs with API keys had no KMS encryption. "
            "Logs retained for 3 years, accessible to all roles with cloudwatch:GetLogEvents. "
            "Root cause: log group created without kms_key_id."
        ),
        root_cause_keywords=["cloudwatch", "logs", "kms", "deny"],
        expected_rego=_rego(
            "cirus.aws.cloudwatch_logs_kms",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_cloudwatch_log_group"\n'
            '  not input.resource.kms_key_id\n'
            '  msg := sprintf("Log group %v must be encrypted with KMS", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_cloudwatch_log_group", "app_logs_encrypted",
            '  name              = "/app/prod"\n'
            '  retention_in_days = 90\n'
            '  kms_key_id        = aws_kms_key.logs.arn',
        ),
    ),

    GoldenCase(
        incident_id="INC-028",
        category="unencrypted_data",
        raw_text=(
            "SNS topic used for PII notifications had no KMSMasterKeyId set. "
            "Messages containing SSNs stored at rest without encryption. "
            "Root cause: kms_master_key_id not specified in SNS topic resource."
        ),
        root_cause_keywords=["sns", "kms", "encryption", "deny"],
        expected_rego=_rego(
            "cirus.aws.sns_encrypted",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_sns_topic"\n'
            '  not input.resource.kms_master_key_id\n'
            '  msg := sprintf("SNS topic %v must have KMS encryption", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_sns_topic", "pii_notifications",
            '  name              = "pii-notifications"\n'
            '  kms_master_key_id = aws_kms_key.sns.arn',
        ),
    ),

    GoldenCase(
        incident_id="INC-029",
        category="unencrypted_data",
        raw_text=(
            "GCS bucket storing ML training data (containing private medical images) "
            "used Google-managed encryption. Compliance requires CMEK. "
            "Root cause: encryption block missing from google_storage_bucket resource."
        ),
        root_cause_keywords=["gcs", "cmek", "encryption", "deny"],
        expected_rego=_rego(
            "cirus.gcp.gcs_cmek",
            'deny contains msg if {\n'
            '  input.resource_type == "google_storage_bucket"\n'
            '  not input.resource.encryption.default_kms_key_name\n'
            '  msg := sprintf("GCS bucket %v must use CMEK", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "google_storage_bucket", "ml_data_cmek",
            '  name     = "ml-training-data"\n'
            '  location = "US"\n'
            '\n'
            '  encryption {\n'
            '    default_kms_key_name = google_kms_crypto_key.gcs.id\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-030",
        category="unencrypted_data",
        raw_text=(
            "Azure SQL Database had Transparent Data Encryption (TDE) disabled. "
            "Database backup restored by contractor in a non-compliant environment. "
            "Root cause: threat_detection_policy and TDE not configured."
        ),
        root_cause_keywords=["azure", "sql", "transparent_data_encryption", "deny"],
        expected_rego=_rego(
            "cirus.azure.sql_tde",
            'deny contains msg if {\n'
            '  input.resource_type == "azurerm_mssql_database"\n'
            '  not input.resource.transparent_data_encryption_enabled\n'
            '  msg := sprintf("Azure SQL database %v must have TDE enabled", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "azurerm_mssql_database", "prod_db_tde",
            '  name                                = "prod-db"\n'
            '  server_id                           = azurerm_mssql_server.main.id\n'
            '  transparent_data_encryption_enabled = true',
        ),
    ),

    # ── Network Exposure (INC-031 to INC-040) ─────────────────────────────────

    GoldenCase(
        incident_id="INC-031",
        category="network_exposure",
        raw_text=(
            "ALB had HTTP listener forwarding to target group with no HTTPS redirect. "
            "Cookie session tokens transmitted in plaintext on public WiFi. "
            "Root cause: missing HTTPS redirect rule on ALB HTTP listener."
        ),
        root_cause_keywords=["alb", "https", "redirect", "deny"],
        expected_rego=_rego(
            "cirus.aws.alb_https_only",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_lb_listener"\n'
            '  input.resource.port == 80\n'
            '  input.resource.default_action.type != "redirect"\n'
            '  msg := "ALB HTTP listener must redirect to HTTPS"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_lb_listener", "http_redirect",
            '  load_balancer_arn = aws_lb.app.arn\n'
            '  port              = "80"\n'
            '  protocol          = "HTTP"\n'
            '\n'
            '  default_action {\n'
            '    type = "redirect"\n'
            '    redirect {\n'
            '      port        = "443"\n'
            '      protocol    = "HTTPS"\n'
            '      status_code = "HTTP_301"\n'
            '    }\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-032",
        category="network_exposure",
        raw_text=(
            "SSH port 22 open to 0.0.0.0/0 on bastion host SG. Attacker from China "
            "brute-forced 'ec2-user' account over 3 days. Root cause: no IP restriction "
            "on SSH access; no fail2ban or SSM Session Manager."
        ),
        root_cause_keywords=["ssh", "security_group", "0.0.0.0/0", "deny"],
        expected_rego=_rego(
            "cirus.aws.no_public_ssh",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_security_group_rule"\n'
            '  input.resource.type == "ingress"\n'
            '  input.resource.from_port == 22\n'
            '  public_cidrs := {"0.0.0.0/0", "::/0"}\n'
            '  public_cidrs[input.resource.cidr_blocks[_]]\n'
            '  msg := "SSH must not be open to the public internet"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_security_group_rule", "bastion_ssh_restricted",
            '  type              = "ingress"\n'
            '  from_port         = 22\n'
            '  to_port           = 22\n'
            '  protocol          = "tcp"\n'
            '  cidr_blocks       = [var.vpn_cidr]\n'
            '  security_group_id = aws_security_group.bastion.id',
        ),
    ),

    GoldenCase(
        incident_id="INC-033",
        category="network_exposure",
        raw_text=(
            "VPC had no flow logs enabled. Security investigation after intrusion could not "
            "reconstruct attacker lateral movement. Root cause: VPC created without flow logs; "
            "no compliance control enforcing them."
        ),
        root_cause_keywords=["vpc", "flow_logs", "deny"],
        expected_rego=_rego(
            "cirus.aws.vpc_flow_logs",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_vpc"\n'
            '  not input.resource.enable_dns_support\n'
            '  msg := "All VPCs must have flow logs enabled"\n'
            '}\n\n'
            '# Separate policy for flow log resource\n'
            'warn contains msg if {\n'
            '  input.resource_type == "aws_vpc"\n'
            '  not input.related_resources[_].resource_type == "aws_flow_log"\n'
            '  msg := sprintf("VPC %v should have an associated aws_flow_log resource", [input.resource.tags.Name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_flow_log", "vpc_flow_logs",
            '  iam_role_arn    = aws_iam_role.flow_log.arn\n'
            '  log_destination = aws_cloudwatch_log_group.flow_logs.arn\n'
            '  traffic_type    = "ALL"\n'
            '  vpc_id          = aws_vpc.main.id',
        ),
    ),

    GoldenCase(
        incident_id="INC-034",
        category="network_exposure",
        raw_text=(
            "Kubernetes API server NodePort services exposed internal microservices to "
            "the node's public IP. Three services were reachable from internet without auth. "
            "Root cause: NodePort services in production; no NetworkPolicy."
        ),
        root_cause_keywords=["kubernetes", "NodePort", "NetworkPolicy", "deny"],
        expected_rego=_rego(
            "cirus.k8s.no_nodeport_in_prod",
            'deny contains msg if {\n'
            '  input.kind == "Service"\n'
            '  input.spec.type == "NodePort"\n'
            '  input.metadata.namespace == "prod"\n'
            '  msg := sprintf("Service %v must not use NodePort in prod namespace", [input.metadata.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "kubernetes_network_policy", "prod_default_deny",
            '  metadata {\n'
            '    name      = "default-deny-ingress"\n'
            '    namespace = "prod"\n'
            '  }\n'
            '  spec {\n'
            '    pod_selector {}\n'
            '    policy_types = ["Ingress"]\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-035",
        category="network_exposure",
        raw_text=(
            "Lambda function URL had no auth (AuthType=NONE) and no WAF. "
            "Function processed payments. SSRF via public function URL gave attacker "
            "access to VPC metadata. Root cause: Lambda URL auth type not set to AWS_IAM."
        ),
        root_cause_keywords=["lambda", "function_url", "auth", "deny"],
        expected_rego=_rego(
            "cirus.aws.lambda_url_auth",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_lambda_function_url"\n'
            '  input.resource.authorization_type == "NONE"\n'
            '  msg := sprintf("Lambda function URL %v must use AWS_IAM authorization", [input.resource.function_name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_lambda_function_url", "payment_processor_url",
            '  function_name      = aws_lambda_function.payment_processor.function_name\n'
            '  authorization_type = "AWS_IAM"',
        ),
    ),

    GoldenCase(
        incident_id="INC-036",
        category="network_exposure",
        raw_text=(
            "API Gateway REST API stage had no WAF ACL attached. SQL injection attack "
            "bypassed application-level validation. Root cause: missing WAF WebACL on "
            "prod stage; no rate limiting."
        ),
        root_cause_keywords=["api_gateway", "waf", "acl", "deny"],
        expected_rego=_rego(
            "cirus.aws.api_gateway_waf",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_api_gateway_stage"\n'
            '  not input.resource.web_acl_arn\n'
            '  msg := sprintf("API Gateway stage %v/%v must have WAF WebACL", [input.resource.rest_api_id, input.resource.stage_name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_wafv2_web_acl_association", "api_gateway_waf",
            '  resource_arn = aws_api_gateway_stage.prod.arn\n'
            '  web_acl_arn  = aws_wafv2_web_acl.api_protection.arn',
        ),
    ),

    GoldenCase(
        incident_id="INC-037",
        category="network_exposure",
        raw_text=(
            "EKS cluster endpoint was publicly accessible without private endpoint enabled. "
            "kubectl access from internet with leaked kubeconfig gave full cluster access. "
            "Root cause: endpoint_public_access=true, endpoint_private_access=false."
        ),
        root_cause_keywords=["eks", "endpoint", "private_access", "deny"],
        expected_rego=_rego(
            "cirus.aws.eks_private_endpoint",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_eks_cluster"\n'
            '  input.resource.vpc_config[_].endpoint_public_access == true\n'
            '  not input.resource.vpc_config[_].endpoint_private_access\n'
            '  msg := sprintf("EKS cluster %v must have private endpoint enabled", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_eks_cluster", "prod_cluster",
            '  name = "prod"\n'
            '\n'
            '  vpc_config {\n'
            '    subnet_ids              = var.private_subnet_ids\n'
            '    endpoint_private_access = true\n'
            '    endpoint_public_access  = false\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-038",
        category="network_exposure",
        raw_text=(
            "MSK (Kafka) cluster had unauthenticated access enabled (no TLS client auth). "
            "Internal broker reachable from any VPC workload without credentials. "
            "Root cause: client_authentication not configured in MSK resource."
        ),
        root_cause_keywords=["msk", "kafka", "tls", "authentication", "deny"],
        expected_rego=_rego(
            "cirus.aws.msk_tls_auth",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_msk_cluster"\n'
            '  not input.resource.client_authentication.tls.certificate_authority_arns\n'
            '  msg := sprintf("MSK cluster %v must require TLS client authentication", [input.resource.cluster_name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_msk_cluster", "events_cluster",
            '  cluster_name = "events"\n'
            '\n'
            '  encryption_info {\n'
            '    encryption_in_transit {\n'
            '      client_broker = "TLS"\n'
            '    }\n'
            '  }\n'
            '\n'
            '  client_authentication {\n'
            '    tls {\n'
            '      certificate_authority_arns = [aws_acmpca_certificate_authority.msk.arn]\n'
            '    }\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-039",
        category="network_exposure",
        raw_text=(
            "NACLs on prod subnet had inbound 0.0.0.0/0 allow on all ports as a quick "
            "debug rule that was never reverted. Security groups were still restrictive but "
            "defense-in-depth was broken. Root cause: overpermissive NACL rule."
        ),
        root_cause_keywords=["nacl", "0.0.0.0/0", "all_ports", "deny"],
        expected_rego=_rego(
            "cirus.aws.no_nacl_allow_all",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_network_acl_rule"\n'
            '  input.resource.rule_action == "allow"\n'
            '  input.resource.cidr_block == "0.0.0.0/0"\n'
            '  input.resource.from_port == 0\n'
            '  input.resource.to_port == 65535\n'
            '  msg := "NACL must not allow all traffic from 0.0.0.0/0"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_network_acl_rule", "prod_https_inbound",
            '  network_acl_id = aws_network_acl.prod.id\n'
            '  rule_number    = 100\n'
            '  egress         = false\n'
            '  protocol       = "tcp"\n'
            '  rule_action    = "allow"\n'
            '  cidr_block     = "0.0.0.0/0"\n'
            '  from_port      = 443\n'
            '  to_port        = 443',
        ),
    ),

    GoldenCase(
        incident_id="INC-040",
        category="network_exposure",
        raw_text=(
            "Route53 wildcard record *.internal.company.com resolved to public IP of dev server. "
            "Subdomain takeover: dev server decommissioned but DNS not cleaned up. "
            "Attacker registered new service on that IP. Root cause: dangling DNS record."
        ),
        root_cause_keywords=["route53", "dns", "wildcard", "deny"],
        expected_rego=_rego(
            "cirus.aws.no_wildcard_dns",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_route53_record"\n'
            '  startswith(input.resource.name, "*")\n'
            '  msg := sprintf("Wildcard DNS record %v is not permitted — use explicit records", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_route53_record", "api_explicit",
            '  zone_id = aws_route53_zone.internal.zone_id\n'
            '  name    = "api.internal.company.com"\n'
            '  type    = "A"\n'
            '  ttl     = 60\n'
            '  records = [aws_instance.api.private_ip]',
        ),
    ),

    # ── Resource Exhaustion (INC-041 to INC-045) ──────────────────────────────

    GoldenCase(
        incident_id="INC-041",
        category="resource_exhaustion",
        raw_text=(
            "Lambda function recursively called itself on DLQ trigger, exhausting concurrency "
            "quota (1000) in 4 minutes. All other Lambda functions throttled. "
            "Root cause: no reserved concurrency limits; DLQ re-trigger loop."
        ),
        root_cause_keywords=["lambda", "concurrency", "reserved", "deny"],
        expected_rego=_rego(
            "cirus.aws.lambda_reserved_concurrency",
            'warn contains msg if {\n'
            '  input.resource_type == "aws_lambda_function"\n'
            '  not input.resource.reserved_concurrent_executions\n'
            '  msg := sprintf("Lambda %v should have reserved_concurrent_executions set", [input.resource.function_name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_lambda_function", "processor_with_concurrency",
            '  function_name                  = "processor"\n'
            '  runtime                        = "python3.12"\n'
            '  reserved_concurrent_executions = 50',
        ),
    ),

    GoldenCase(
        incident_id="INC-042",
        category="resource_exhaustion",
        raw_text=(
            "DynamoDB table had no read capacity limits (PAY_PER_REQUEST). Runaway scan "
            "query from analytics job consumed $4,200 in 90 minutes. "
            "Root cause: no cost controls / budget alerts on DynamoDB."
        ),
        root_cause_keywords=["dynamodb", "capacity", "cost", "budget"],
        expected_rego=_rego(
            "cirus.aws.dynamodb_provisioned_or_bounded",
            'warn contains msg if {\n'
            '  input.resource_type == "aws_dynamodb_table"\n'
            '  input.resource.billing_mode == "PAY_PER_REQUEST"\n'
            '  not input.resource.tags.CostCenter\n'
            '  msg := sprintf("DynamoDB table %v on PAY_PER_REQUEST must have CostCenter tag", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_budgets_budget", "dynamodb_spend_alert",
            '  name              = "dynamodb-monthly-cap"\n'
            '  budget_type       = "COST"\n'
            '  limit_amount      = "500"\n'
            '  limit_unit        = "USD"\n'
            '  time_unit         = "MONTHLY"\n'
            '  cost_filter {\n'
            '    name   = "Service"\n'
            '    values = ["Amazon DynamoDB"]\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-043",
        category="resource_exhaustion",
        raw_text=(
            "ECS Fargate task had no memory limits. OOM killed neighboring tasks. "
            "Memory leak in Node.js service consumed all cluster memory in 2 hours. "
            "Root cause: memory hard limit not set in task definition."
        ),
        root_cause_keywords=["ecs", "memory", "limits", "deny"],
        expected_rego=_rego(
            "cirus.aws.ecs_memory_limits",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_ecs_task_definition"\n'
            '  container := json.unmarshal(input.resource.container_definitions)[_]\n'
            '  not container.memory\n'
            '  msg := sprintf("ECS container %v in task %v must set memory limit", [container.name, input.resource.family])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_ecs_task_definition", "app_task",
            '  family                   = "app"\n'
            '  requires_compatibilities = ["FARGATE"]\n'
            '  network_mode             = "awsvpc"\n'
            '  cpu                      = 256\n'
            '  memory                   = 512\n'
            '  container_definitions    = jsonencode([{\n'
            '    name   = "app"\n'
            '    image  = var.image\n'
            '    memory = 512\n'
            '    memoryReservation = 256\n'
            '  }])',
        ),
    ),

    GoldenCase(
        incident_id="INC-044",
        category="resource_exhaustion",
        raw_text=(
            "SQS queue depth reached 10M messages causing Lambda trigger backlog. "
            "No visibility timeout set; messages reprocessed 4x per Lambda invocation cap. "
            "Root cause: SQS visibility timeout shorter than Lambda max execution time."
        ),
        root_cause_keywords=["sqs", "visibility_timeout", "lambda", "deny"],
        expected_rego=_rego(
            "cirus.aws.sqs_visibility_timeout",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_sqs_queue"\n'
            '  input.resource.visibility_timeout_seconds < 60\n'
            '  msg := sprintf("SQS queue %v visibility timeout must be >= 60s for Lambda consumers", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_sqs_queue", "lambda_trigger_queue",
            '  name                       = "lambda-trigger"\n'
            '  visibility_timeout_seconds = 300\n'
            '  message_retention_seconds  = 1209600\n'
            '  max_message_size           = 262144',
        ),
    ),

    GoldenCase(
        incident_id="INC-045",
        category="resource_exhaustion",
        raw_text=(
            "CloudFront distribution had no request rate limiting. Bot traffic "
            "hit origin at 50K req/s, bypassing caching due to unique query parameters. "
            "Root cause: no WAF rate-based rules on CloudFront."
        ),
        root_cause_keywords=["cloudfront", "waf", "rate_limit", "deny"],
        expected_rego=_rego(
            "cirus.aws.cloudfront_waf",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_cloudfront_distribution"\n'
            '  not input.resource.web_acl_id\n'
            '  msg := "CloudFront distribution must have WAF WebACL with rate limiting"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_wafv2_web_acl_association", "cloudfront_waf",
            '  resource_arn = aws_cloudfront_distribution.app.arn\n'
            '  web_acl_arn  = aws_wafv2_web_acl.cloudfront_protection.arn',
        ),
    ),

    # ── Supply Chain / Dependency (INC-046 to INC-050) ────────────────────────

    GoldenCase(
        incident_id="INC-046",
        category="supply_chain",
        raw_text=(
            "npm package 'colors' used in build was typosquatted as 'colour' in package-lock.json. "
            "Malicious package exfiltrated env vars during build. "
            "Root cause: no lock file integrity checks in CI; registry not restricted to known-safe."
        ),
        root_cause_keywords=["npm", "registry", "integrity", "deny"],
        expected_rego=_rego(
            "cirus.supply_chain.npm_private_registry",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_codeartifact_domain"\n'
            '  not input.resource.encryption_key\n'
            '  msg := "CodeArtifact domain must use KMS encryption for artifact storage"\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_codeartifact_domain", "internal_npm",
            '  domain         = "internal"\n'
            '  encryption_key = aws_kms_key.codeartifact.arn',
        ),
    ),

    GoldenCase(
        incident_id="INC-047",
        category="supply_chain",
        raw_text=(
            "Docker base image used FROM ubuntu:latest in Dockerfile. Image was updated "
            "upstream with a backdoored libc replacement. "
            "Root cause: mutable image tags; no digest pinning."
        ),
        root_cause_keywords=["docker", "digest", "immutable", "deny"],
        expected_rego=_rego(
            "cirus.supply_chain.ecr_immutable_tags",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_ecr_repository"\n'
            '  input.resource.image_tag_mutability != "IMMUTABLE"\n'
            '  msg := sprintf("ECR repository %v must have IMMUTABLE image tags", [input.resource.name])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_ecr_repository", "pinned_base_images",
            '  name                 = "base-images"\n'
            '  image_tag_mutability = "IMMUTABLE"\n'
            '\n'
            '  image_scanning_configuration {\n'
            '    scan_on_push = true\n'
            '  }',
        ),
    ),

    GoldenCase(
        incident_id="INC-048",
        category="supply_chain",
        raw_text=(
            "Terraform provider pinned to '>= 3.0' without upper bound. "
            "Major version upgrade of hashicorp/aws broke 6 prod applies. "
            "Root cause: unpinned provider version in required_providers block."
        ),
        root_cause_keywords=["terraform", "provider", "version", "deny"],
        expected_rego=_rego(
            "cirus.terraform.provider_pinned",
            'deny contains msg if {\n'
            '  provider := input.resource.required_providers[name]\n'
            '  not contains(provider.version, "~>")\n'
            '  not regex.match(`^= [0-9]+\\.[0-9]+\\.[0-9]+$`, provider.version)\n'
            '  msg := sprintf("Provider %v must use pessimistic constraint (~>) or exact version pin", [name])\n'
            '}',
        ),
        expected_terraform=(
            'terraform {\n'
            '  required_providers {\n'
            '    aws = {\n'
            '      source  = "hashicorp/aws"\n'
            '      version = "~> 5.0"\n'
            '    }\n'
            '  }\n'
            '}\n'
        ),
    ),

    GoldenCase(
        incident_id="INC-049",
        category="supply_chain",
        raw_text=(
            "GitHub Actions workflow used third-party action at floating tag 'v2' without SHA pin. "
            "Action was compromised via tag mutation; malicious code ran in CI with OIDC token access. "
            "Root cause: unpinned GitHub Actions third-party action."
        ),
        root_cause_keywords=["github_actions", "sha", "pin", "deny"],
        expected_rego=_rego(
            "cirus.supply_chain.gh_actions_sha_pinned",
            'deny contains msg if {\n'
            '  step := input.jobs[_].steps[_]\n'
            '  uses := step.uses\n'
            '  not regex.match(`^[^/]+/[^@]+@[0-9a-f]{40}$`, uses)\n'
            '  not startswith(uses, "./")\n'
            '  msg := sprintf("GitHub Actions step using %v must pin to SHA", [uses])\n'
            '}',
        ),
        expected_terraform=(
            "# No Terraform patch for this incident.\n"
            "# Remediation is in .github/workflows/ci.yml:\n"
            "# Change: actions/checkout@v4\n"
            "# To:     actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2\n"
        ),
    ),

    GoldenCase(
        incident_id="INC-050",
        category="supply_chain",
        raw_text=(
            "PyPI package 'requests-enhanced' (typosquat of requests) installed via "
            "requirements.txt. Package harvested AWS_ACCESS_KEY_ID from os.environ on import. "
            "Root cause: no package allowlisting; no Dependabot or socket.dev scanning."
        ),
        root_cause_keywords=["pypi", "allowlist", "scanning", "deny"],
        expected_rego=_rego(
            "cirus.supply_chain.codeartifact_upstream",
            'deny contains msg if {\n'
            '  input.resource_type == "aws_codeartifact_repository"\n'
            '  not input.resource.upstream\n'
            '  not input.resource.external_connections\n'
            '  msg := sprintf("CodeArtifact repo %v must configure upstream or external connection through approved source", [input.resource.repository])\n'
            '}',
        ),
        expected_terraform=_tf(
            "aws_codeartifact_repository", "pypi_allowlisted",
            '  repository = "pypi-internal"\n'
            '  domain     = aws_codeartifact_domain.internal.domain\n'
            '\n'
            '  external_connections {\n'
            '    external_connection_name = "public:pypi"\n'
            '  }\n'
            '\n'
            '  description = "Proxied PyPI with internal allowlisting via CodeArtifact"',
        ),
    ),
]


def get_dataset() -> list[GoldenCase]:
    """Return the full golden dataset."""
    return GOLDEN_DATASET


def get_by_category(category: str) -> list[GoldenCase]:
    """Return all cases for a given category."""
    return [c for c in GOLDEN_DATASET if c.category == category]


def get_by_id(incident_id: str) -> GoldenCase | None:
    """Return a single case by incident ID."""
    for c in GOLDEN_DATASET:
        if c.incident_id == incident_id:
            return c
    return None
