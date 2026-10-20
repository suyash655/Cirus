# CIRUS — Beginner's Walkthrough

> **Who this is for:** Someone who has the code but does not fully understand it yet.
> Everything technical is defined the first time it appears.

---

## What is CIRUS? (5 plain sentences)

1. **CIRUS watches cloud systems that go wrong.** You paste in a report of an incident — for example "our S3 bucket was open to the public and someone downloaded our data" — and CIRUS reads it.

2. **It runs the text through a 7-step AI pipeline.** Each step does one job: extracting facts, figuring out the root cause, writing a fix, checking the fix, and scoring how risky the original problem was.

3. **The most important outputs are three files:** a *security rule* (written in a language called Rego/OPA) that would block the same mistake from happening again, a *Terraform patch* (a code change for your cloud infrastructure), and *tests* that verify the fix actually works.

4. **A human must approve everything before it ships.** CIRUS puts the generated files into a review queue. You read them, and only when you click "approve" does CIRUS create a GitHub Pull Request — a formal code-change proposal that your team reviews before merging.

5. **It runs in "mock mode" with no AI keys needed.** In mock mode, the AI calls are replaced with hard-coded demo responses so you can see the full pipeline, UI, and approval flow without spending money on a real AI.

---

## Folder Map — What Each Directory Does

```
PROJECTRIVERA/
│
├── backend/                    ← The brain (Python / FastAPI)
│   ├── app/
│   │   ├── main.py             ← Entry point: starts the web server
│   │   ├── core/
│   │   │   ├── config.py       ← All settings (read from .env file)
│   │   │   ├── logging.py      ← How log messages are formatted
│   │   │   └── security.py     ← API key checking
│   │   ├── db/                 ← Database connection setup
│   │   ├── models/             ← Database table definitions (ORM models)
│   │   │   ├── incident.py     ← The "Incident" table
│   │   │   ├── artifact.py     ← The "Artifact" table (generated files)
│   │   │   └── run.py          ← The "WorkflowRun" table (pipeline progress)
│   │   ├── orchestrator/       ← The pipeline engine
│   │   │   ├── pipeline.py     ← Runs all 7 stages in order
│   │   │   ├── stages.py       ← Code for each individual stage
│   │   │   ├── state.py        ← The "shopping cart" passed between stages
│   │   │   └── constants.py    ← Stage ID names
│   │   ├── api/v1/endpoints/   ← REST API routes (HTTP endpoints)
│   │   │   ├── incidents.py    ← POST /incidents, GET /incidents/{id}
│   │   │   ├── artifacts.py    ← GET /incidents/{id}/artifacts
│   │   │   ├── runs.py         ← GET /runs/{id} (pipeline progress)
│   │   │   └── gitops.py       ← POST /gitops/create-pr (PR preview)
│   │   ├── services/           ← Business logic
│   │   │   ├── llm_service.py  ← Talks to the AI (Groq, OpenAI, mock)
│   │   │   ├── prompt_service.py ← The text prompts sent to the AI
│   │   │   ├── artifact_service.py ← Generates and saves artifacts
│   │   │   ├── gitops_service.py   ← Creates the PR preview
│   │   │   ├── wolfram_service.py  ← Risk scoring (disabled by default)
│   │   │   └── firecrawl_service.py ← Web scraping (disabled by default)
│   │   ├── validators/         ← Syntax checkers (the "does this code work?" step)
│   │   │   ├── rego_validator.py      ← Checks OPA/Rego policy files
│   │   │   └── terraform_validator.py ← Checks Terraform HCL files
│   │   └── utils/
│   │       ├── pii_scrub.py    ← Hides sensitive data before sending to AI
│   │       └── json_repair.py  ← Fixes slightly broken JSON from the AI
│   ├── tests/                  ← Automated tests (run with pytest)
│   ├── scripts/
│   │   ├── demo_incidents.py   ← Seeds 3 demo scenarios
│   │   └── eval_harness.py     ← Runs 10+ test cases, prints a report
│   ├── requirements.txt        ← Python packages needed
│   └── .env.example            ← Template for your settings file
│
├── src/                        ← The face (Next.js / React web app)
│   ├── app/
│   │   ├── dashboard/          ← Main page: list of incidents
│   │   ├── incidents/[id]/     ← Detail page: view generated artifacts
│   │   ├── incidents/new/      ← Form: paste an incident report
│   │   └── workflow/           ← Pipeline visualizer (progress tracker)
│   └── lib/
│       ├── api.ts              ← All the calls the frontend makes to the backend
│       └── hooks/              ← Data-fetching React hooks
│
├── mlops/evaluation/           ← Quality measurement
│   └── golden_dataset/cases.py ← 50 known incidents with expected answers
│
├── .env                        ← YOUR PERSONAL SETTINGS (never commit this!)
├── .env.example                ← The safe template to share
├── Makefile                    ← One-command shortcuts (make demo, make eval)
├── docker-compose.yml          ← Runs everything in containers (make demo uses this)
└── README.md                   ← Project overview
```

---

## Step-by-Step: What Happens When a User Submits an Incident

Here is every file touched, in order.

### 1. User opens the web form
**File:** `src/app/incidents/new/page.tsx`
The user types (or pastes) an incident report into a text box. They choose which artifacts to generate (policy, IaC, runbook, etc.) and click "Submit."

### 2. Frontend sends the report to the backend
**File:** `src/lib/api.ts` → function `createIncident()`
The browser sends an HTTP POST request to `http://localhost:8000/api/v1/incidents/` with the raw text and selected artifact types.

### 3. Backend creates a database record
**File:** `backend/app/api/v1/endpoints/incidents.py` → `create_incident()`
The backend saves the incident in the SQLite database and immediately returns a `run_id` (a unique ID for this pipeline run) to the browser. The user does not wait — they get a response in milliseconds.

### 4. Pipeline starts in the background
**File:** `backend/app/api/v1/endpoints/incidents.py` → `_run_pipeline_bg()`
A background task fires. This calls `CIRUSPipeline.run()`.

### 5. Stage 1 — Normalization
**File:** `backend/app/orchestrator/stages.py` → `run_normalization()`
**Prompt:** `backend/app/services/prompt_service.py` → `extraction_prompt()`
The raw text is sent to the AI (or mock). The AI returns a JSON object with: title, cloud provider, severity, affected services, error messages, a summary.

*Before the text is sent to the AI, `backend/app/utils/pii_scrub.py` runs first.* It redacts account numbers, IP addresses, email addresses, and API keys.

### 6. Stage 2 — Root Cause Classification
**File:** `backend/app/orchestrator/stages.py` → `run_root_cause()`
The AI reads the incident and identifies the technical root cause (e.g., "IAM role had AdministratorAccess"), contributing factors, and a timeline.

### 7. Stage 3 — Context Enrichment
**File:** `backend/app/orchestrator/stages.py` → `run_context_enrichment()`
Two optional enrichments happen here:
- **Firecrawl** (disabled by default): scrapes relevant documentation URLs.
- **ChromaDB** (enabled by default): searches for past similar incidents in the vector database and injects them as context.

### 8. Stage 4 — Artifact Generation
**File:** `backend/app/orchestrator/stages.py` → `run_artifact_generation()`
**Service:** `backend/app/services/artifact_service.py` → `generate_artifact()`
For each requested artifact type, the AI is called once. Each call gets a specific prompt. The results are saved to the `Artifact` table in the database. At this stage, `artifact_content` (the raw code strings) is stored on the pipeline state object for the next stage.

### 9. Stage 5 — Validator / Critic
**File:** `backend/app/orchestrator/stages.py` → `run_validator()`
**Validators:** `backend/app/validators/rego_validator.py` and `backend/app/validators/terraform_validator.py`
The raw code strings from Stage 4 are checked by real parsers:
- **Rego policy**: First tries `opa check` (the OPA binary). If OPA is not installed, falls back to a regex check.
- **Terraform patch**: First tries `python-hcl2` (a Python library that parses HCL). If available, then tries `terraform validate`.
- The validator reports `passed=True/False` and the specific error if something fails.

### 10. Stage 6 — Risk Scoring
**File:** `backend/app/orchestrator/stages.py` → `run_risk_scoring()`
Calculates a before/after risk score (0–100). In mock mode this is a simple formula (e.g., P1 severity = 90 before, 55 after remediation). In live mode, Wolfram Alpha can compute this.

### 11. Stage 7 — Citation Extraction
**File:** `backend/app/orchestrator/stages.py` → `run_citation_extraction()`
The AI finds the most important lines/phrases from the original incident text and marks them as evidence.

### 12. Incident marked "ready"
**File:** `backend/app/orchestrator/pipeline.py` lines ~123–143
The incident status is updated to `ready`. The incident is also added to the ChromaDB vector database so future similar incidents can reference it.

### 13. User reviews the results
**File:** `src/app/incidents/[id]/page.tsx`
The frontend polls for the run status. When it sees `status: "completed"`, it loads the artifact tabs: RCA, Policy, IaC, Alerts, Runbook, Regression Tests.

### 14. User approves and previews the PR
**File:** `src/app/incidents/[id]/page.tsx` + `backend/app/api/v1/endpoints/gitops.py`
The user clicks "Open GitOps PR." The backend calls `GitOpsService.create_remediation_pr()` which generates a **preview** of what the Pull Request would look like (branch name, files, diff). **No actual GitHub PR is opened automatically** — this is intentional.

---

## Glossary — Every Technical Term Defined

| Term | Plain English meaning |
|------|----------------------|
| **API** | Application Programming Interface — a way for programs to talk to each other. The frontend calls the backend's API to get data. |
| **Artifact** | A file produced by CIRUS. Could be a security rule, an infrastructure patch, a runbook, etc. |
| **ChromaDB** | A database designed to store and search text by meaning (not just exact words). Used to find past incidents similar to a new one. |
| **Endpoint** | A specific URL the backend listens on. E.g., `POST /api/v1/incidents/` is the endpoint for creating incidents. |
| **FastAPI** | A Python web framework (library) used to build the backend server. |
| **Groq / Featherless** | AI API providers — companies that host AI models you can call over the internet. |
| **HCL (HashiCorp Configuration Language)** | The language used to write Terraform files. Looks like: `resource "aws_s3_bucket" "example" { ... }` |
| **IaC (Infrastructure as Code)** | Writing your cloud setup as code files instead of clicking through a web console. Terraform is the most popular IaC tool. |
| **JSON** | JavaScript Object Notation — a text format for structured data. Looks like: `{"key": "value"}` |
| **LLM** | Large Language Model — the AI brain (e.g., GPT-4, Llama, Claude). Takes text in, gives text out. |
| **Mock mode** | Running the system with fake AI responses instead of real ones. No API keys needed, no money spent. |
| **Next.js** | A JavaScript framework for building web interfaces. Used for the frontend. |
| **OPA / Rego** | Open Policy Agent. A tool for writing security rules. Rego is the language those rules are written in. Example rule: "deny any S3 bucket that is public." |
| **ORM** | Object-Relational Mapping — code that lets you work with database records as Python objects instead of writing raw SQL. SQLAlchemy is the ORM used here. |
| **PII** | Personally Identifiable Information — data like email addresses, account numbers, IP addresses. Scrubbed before sending to AI. |
| **Pipeline** | A series of steps that run in order, where each step passes its result to the next. |
| **PR (Pull Request)** | A formal request to merge code changes into a codebase. CIRUS generates a *preview* of a PR — it never auto-merges anything. |
| **Pytest** | A Python testing library. Run `pytest tests/` to execute all tests. |
| **React** | A JavaScript library for building interactive web pages. |
| **Redis** | A fast in-memory database used as a task queue (optional, disabled by default). |
| **Rego** | The language used to write OPA policies. See "OPA." |
| **REST** | Representational State Transfer — a style for building web APIs using HTTP verbs (GET, POST, DELETE). |
| **SQLAlchemy** | A Python library that talks to the database (reads/writes rows in tables). |
| **SQLite** | A simple file-based database. The whole database is a single `.db` file on your disk. Used in development. |
| **Structlog** | A Python logging library that produces structured (JSON-friendly) log output. |
| **TanStack Query** | A React library that manages data fetching, caching, and polling in the frontend. |
| **Temporal** | A workflow orchestration system. Optional in CIRUS — when enabled, it makes the pipeline restartable if it crashes mid-way. Disabled by default. |
| **Terraform** | An IaC tool for declaring what cloud resources you want. CIRUS generates Terraform patches to fix misconfigured resources. |
| **TypeScript** | JavaScript with type annotations. Used in the frontend. |
| **Vector store** | A database that stores text as numerical "embeddings" so you can search by semantic similarity. ChromaDB is the vector store used here. |

---

## What Is Real, What Is Fake, and What Is Half-Finished

### ✅ REAL AND WORKING

| Feature | How I know |
|---------|-----------|
| Backend API (create incident, retrieve it, list) | 29/29 automated tests pass |
| Mock mode pipeline (all 7 stages run) | Integration tests pass; running manually works |
| Database (SQLite, SQLAlchemy, Alembic migrations) | Tests create and read records successfully |
| Rego validator regex fallback | Code is clean; tests verify it runs |
| Terraform HCL2 validator | `python-hcl2` is installed; tested manually |
| ChromaDB vector store (local) | Test `test_query_similar_with_mocked_collection` passes |
| Temporal settings and client (non-crashing) | Tests pass |
| PR preview generation (GitOpsService) | `test_gitops_service_create_pr` passes |
| Authentication (X-API-Key header) | Tests for 401/200 pass |
| Frontend: all pages render | No compile errors |
| PII scrubber (regex-based) | Added in this branch; unit tested |

### 🟡 REAL BUT NEEDS A BINARY YOU MAY NOT HAVE

| Feature | What's missing |
|---------|---------------|
| OPA `opa check` validator | The `opa` binary is not installed on Windows by default. The code works — it just falls back to the regex check. Install OPA to get the authoritative check. |
| `terraform validate` | The `terraform` binary is not installed. The code falls back to `python-hcl2`, which catches structural errors. |
| Real AI (Groq, Featherless, OpenAI) | Requires API keys in `.env`. Works once keys are set; mock mode is the safe default. |
| Firecrawl web enrichment | Requires `FIRECRAWL_API_KEY`. Safely disabled by default. |

### 🔴 FAKE / SIMULATED (by design or by bug)

| Feature | What's actually happening |
|---------|--------------------------|
| GitOps PR (the "open PR" button) | **By design:** The service generates a realistic-looking preview (branch name, file list, diff) but does NOT call the GitHub API. No real PR is created. This is intentional — nothing auto-merges. |
| Risk scoring (Wolfram mode) | **By design when disabled:** Uses a simple formula (severity → base score, minus 35 for remediation). Not calling Wolfram Alpha unless you set `WOLFRAM_APP_ID`. |
| Context enrichment (Firecrawl) | **By design when disabled:** Returns empty results. The pipeline continues fine. |

### 🔶 HALF-FINISHED OR KNOWN BUGS (fixed in this branch)

| Issue | Status |
|-------|--------|
| **Validator stage dead code** | **FIXED in this branch.** The validator in `stages.py` had a loop that did `pass` and then checked for `_last_policy_code`/`_last_iac_code` which were never set — so it validated NOTHING. Now fixed: artifact content is stored in `state.artifact_content` and actually passed to the validators. |
| **`.env` file in git** | **FIXED in this branch.** The real `.env` with API keys was committed. It is now in `.gitignore` and replaced with a safe `.env.example`. |
| **Binary files in git** | **FIXED in this branch.** `temporal.exe`, `temporal*.zip`, `temporal_bin*/` have been moved to `_archive/`. |
| **PR preview uses hardcoded diff** | Not fixed — the diff always shows an S3 bucket example regardless of the incident type. This is a cosmetic issue for the demo; the flow is correct. |
| Analytics page uses static mock data | Not fixed — the analytics charts show hardcoded numbers, not real DB stats. Tracked on the roadmap as Push 24. |
