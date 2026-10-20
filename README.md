<div align="center">

# CIRUS

**Cloud Incident Response & Unified Remediation System**

*Paste a cloud incident report. Get verified security policies (OPA/Rego), infrastructure patches (Terraform HCL), and automated regression tests.*

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Tests](https://img.shields.io/badge/Tests-32%20passing-brightgreen?style=flat-square)](backend/tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Architecture Walkthrough](WALKTHROUGH.md) · [Archive Log](ARCHIVE_LOG.md) · [API Docs (Local)](http://localhost:8000/docs)

</div>

---

## What CIRUS Does

When a cloud outage or security misconfiguration occurs, teams write incident reports that are often forgotten until the exact same problem recurs months later.

**CIRUS prevents repeats by automating the remediation and prevention loop:**
1. **Reads Incident Reports:** Accepts raw incident text (CloudTrail alerts, post-mortems, or markdown logs).
2. **Protects Privacy (PII Scrubbing):** Redacts sensitive account IDs, IP addresses, email addresses, and API credentials before sending prompts to AI models.
3. **Generates Prevention Artifacts:** Produces an OPA/Rego security policy, a Terraform HCL infrastructure patch, unit tests, a root-cause analysis (RCA), an operational runbook, and detection alerts.
4. **Actually Checks Syntax with Real Parsers:** Validates Rego policies with `opa check` (falling back to AST syntax verification) and validates Terraform with `python-hcl2` and `terraform validate`.
5. **Human Approval & PR Preview:** Generated changes sit in an approval queue. The GitOps action creates a clean **pull request preview** — nothing is ever merged or applied automatically.

---

## What Is Real vs. What Is Mock

| Component | Status | Details |
|-----------|--------|---------|
| **Backend REST API** | Real | FastAPI server with 32 passing automated unit and integration tests. |
| **Frontend Web App** | Real | Next.js 15 App Router interface compiled with 0 errors across all routes. |
| **PII Scrubber** | Real | Pre-prompt sanitizer redacts emails, IPs, account IDs, and API keys. |
| **OPA / Rego Validator** | Real | Checks policies with `opa check` / `opa test` when installed; regex canary fallback. |
| **Terraform HCL Validator**| Real | Structural AST validation via `python-hcl2` and full schema via `terraform validate`. |
| **Vector Similarity (RAG)**| Real | Local ChromaDB vector database stores incidents and queries similar past cases. |
| **GitOps PR** | Preview Only | Generates realistic branch names, diffs, and review previews. No real code auto-merges. |
| **Evaluation Harness** | Real | `make eval` benchmarks 10+ incidents and outputs pass rate tables (labels mock vs. live). |

---

## Quick Start (On Any Brand-New Computer)

### Option A: The One-Command Demo (Docker)

If you have Docker installed, the fastest way to run everything (with `opa` and `terraform` pre-installed inside the container) is:

```bash
# 1. Clone the repository
git clone https://github.com/suyash655/cirus.git
cd cirus

# 2. Launch the demo (seeds 3 sample incidents and starts backend + frontend)
make demo
```

*(If you don't have `make` installed on Windows, run `python backend/scripts/demo_incidents.py` and then `docker-compose up --build`)*

- **Web Dashboard:** [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- **API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option B: Local Setup Without Docker

#### 1. Backend Setup (Python 3.11+)

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed the 3 demo incidents into the local database
python scripts/demo_incidents.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The API is running at `http://localhost:8000`.

#### 2. Frontend Setup (Node.js 18+)

In a new terminal from the project root:

```bash
# Install dependencies
npm install

# Start the frontend dev server
npm run dev
```

Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard) in your browser.

---

## 3 Preloaded Demo Incidents

CIRUS comes pre-seeded with 3 realistic scenarios where a generated policy truly prevents a repeat:

1. **`inc-demo-001-s3` — AWS S3 Bucket Made Public:**
   - *Problem:* A Terraform update dropped the public access block on a customer data bucket.
   - *Prevention:* Generates an OPA/Rego rule denying any `aws_s3_bucket` without `public_access_block`, plus the Terraform HCL fix and regression tests.
2. **`inc-demo-002-firewall` — Security Group Ingress Open to 0.0.0.0/0 on Port 22:**
   - *Problem:* Ad-hoc debugging left SSH port 22 open to the public internet.
   - *Prevention:* Generates a policy denying `0.0.0.0/0` on port 22 and restricts ingress to internal VPN CIDRs.
3. **`inc-demo-003-db` — Unencrypted RDS PostgreSQL Database Volume:**
   - *Problem:* Development Terraform flag (`storage_encrypted = false`) was promoted to production.
   - *Prevention:* Enforces KMS storage encryption on all `aws_db_instance` resources.

---

## Running Verification & Tests

### Automated Test Suite (32 Tests)

Run all unit and integration tests:

```bash
# Using make:
make test

# Or directly:
pytest backend/tests/
```

*Result: 32 passed in ~1 minute (tests PII scrubber, Rego validator, Terraform validator, API endpoints, retry engine, GitOps preview, vector store, and pipeline stages).*

---

### Benchmark Evaluation Harness (`make eval`)

CIRUS includes an evaluation harness that tests 10 diverse benchmark incident categories against AST parsers, keyword requirements, and PII protection:

```bash
# Using make:
make eval

# Or directly:
python backend/scripts/eval_harness.py
```

Sample output:
```text
================================================================================
  CIRUS INCIDENT REMEDIATION EVALUATION HARNESS
================================================================================
  Execution Mode : MOCK (Synthetic Baseline)
  Total Test Cases: 10
  PII Protection : ENABLED (Regex redaction verified)
================================================================================

| Case ID  | Category             | Rego AST     | HCL2 AST     | KW Cov   | Status |
|----------|----------------------|--------------|--------------|----------|--------|
| INC-001  | iam_misconfig        | PASS (regex) | PASS (hcl2)  | 100%     | PASS   |
| INC-003  | iam_misconfig        | PASS (regex) | PASS (hcl2)  | 75%      | PASS   |
| INC-007  | iam_misconfig        | PASS (regex) | PASS (hcl2)  | 80%      | PASS   |
| INC-011  | public_storage       | PASS (regex) | PASS (hcl2)  | 100%     | PASS   |
| INC-015  | public_storage       | PASS (regex) | PASS (hcl2)  | 100%     | PASS   |
| INC-021  | unencrypted_data     | PASS (regex) | PASS (hcl2)  | 75%      | PASS   |
| INC-025  | unencrypted_data     | PASS (regex) | PASS (hcl2)  | 80%      | PASS   |
| INC-031  | network_exposure     | PASS (regex) | PASS (hcl2)  | 100%     | PASS   |
| INC-035  | network_exposure     | PASS (regex) | PASS (hcl2)  | 100%     | PASS   |
| INC-046  | supply_chain         | PASS (regex) | PASS (hcl2)  | 75%      | PASS   |
|----------|----------------------|--------------|--------------|----------|--------|

================================================================================
  EVALUATION SUMMARY
  Mode           : MOCK (Synthetic Baseline)
  Total Cases    : 10
  Passed         : 10
  Pass Rate      : 100.0%
================================================================================
  REMINDER: Results above reflect MOCK baseline fixtures, not real AI quality.
================================================================================
```

---

## Configuration

CIRUS runs in **Mock mode by default** (`MODE=mock`), so you never need an external AI API key or credit card to explore the full product.

To connect live AI providers, copy `.env.example` to `.env` in `backend/` and set:

```env
MODE=live
LLM_PROVIDER=groq          # Options: groq, openai, anthropic, featherless
GROQ_API_KEY=gsk_...
```

---

## Folder Map

For a full beginner explanation of every single folder and file, see [WALKTHROUGH.md](WALKTHROUGH.md).

```text
PROJECTRIVERA/
├── backend/                    # Python / FastAPI server
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST endpoints (incidents, artifacts, runs, gitops)
│   │   ├── models/             # SQLAlchemy ORM database models
│   │   ├── orchestrator/       # 7-stage remediation pipeline
│   │   ├── services/           # LLM router, prompts, GitOps preview, vector store
│   │   ├── validators/         # OPA Rego and Terraform HCL syntax validators
│   │   └── utils/              # PII scrubber, JSON repair, retries
│   ├── scripts/
│   │   ├── demo_incidents.py   # Populates the 3 demo incidents
│   │   └── eval_harness.py     # Benchmark evaluation runner
│   └── tests/                  # 32 automated unit and integration tests
├── src/                        # Next.js 15 / React frontend
│   ├── app/                    # Dashboard, incident detail, new incident form
│   └── components/             # Artifact tabs, pipeline progress tracker
├── _archive/                   # Preserved historical binaries and early test scripts
├── ARCHIVE_LOG.md              # Log of all preserved files and why they were archived
├── WALKTHROUGH.md              # Plain-English guide for students and beginners
├── Makefile                    # make demo, make eval, make test shortcuts
└── docker-compose.yml          # Container configuration with OPA & Terraform
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
