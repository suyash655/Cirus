<div align="center">

# CIRUS

**Cloud Incident Response & Unified Remediation System**

Turn cloud incident reports into production-ready prevention artifacts — policy-as-code, IaC patches, alert rules, runbooks, and regression tests — in under 2 minutes.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Live Demo](#) · [API Docs](http://localhost:8000/docs) · [Report a Bug](../../issues)

</div>

---

## What is CIRUS?

Most teams write a post-mortem, file a ticket, and move on. The same class of incident recurs 6 months later.

CIRUS breaks that loop. You paste an incident report — CloudTrail logs, a Slack thread, a PagerDuty export, anything — and a multi-stage AI pipeline produces:

| Artifact | Format | Purpose |
|---|---|---|
| **Root Cause Analysis** | Markdown | Executive summary, timeline, action items |
| **Policy-as-Code** | OPA/Rego or AWS SCP | Prevents the exact misconfiguration from recurring |
| **IaC Patch** | Terraform / CDK diff | Ready-to-merge infrastructure fix |
| **Alert Rules** | Prometheus / CloudWatch YAML | Detects the same failure pattern < 60s next time |
| **Runbook** | Markdown | Step-by-step on-call response guide |
| **Regression Tests** | pytest / Jest | Automated verification the fix holds |

Every artifact is validated by a critic model before it reaches you. Nothing ships without a human approval step.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CIRUS Pipeline                           │
│                                                                 │
│  Incident  ──►  Normalize  ──►  Root Cause  ──►  Enrich        │
│   Input           (LLM)       Classification    (RAG + docs)   │
│                                                                 │
│  Generate  ──►  Validate  ──►  Risk Score  ──►  Citations      │
│  (6 artifacts)  (Critic)      (0–100 delta)    (evidence)      │
└─────────────────────────────────────────────────────────────────┘
         │                                           │
    FastAPI backend                          Next.js 15 frontend
    SQLite / PostgreSQL                      React 19 + TanStack Query
    Celery + Redis (optional)                Recharts + Framer Motion
    Temporal workflows (optional)            Zustand state
```

### Key design decisions

- **Mock mode** — The entire pipeline runs with `MODE=mock` / `LLM_PROVIDER=mock`. Zero API keys needed to run locally and see real UI flows.
- **Provider-agnostic LLM router** — Swap between OpenAI, Anthropic, Groq, or Featherless by changing one env var. No code changes.
- **Validator/Critic stage** — A second model pass checks every generated artifact for syntax errors and hallucinations before it surfaces.
- **Human approval gate** — Nothing merges automatically. Every generated guardrail waits in a review queue.

---

## Project structure

```
cirus/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST endpoints (incidents, artifacts, runs, dashboard)
│   │   ├── core/               # Config, security, logging, errors
│   │   ├── db/                 # SQLAlchemy async session + base
│   │   ├── models/             # ORM models (Incident, Artifact, WorkflowRun, Citation)
│   │   ├── orchestrator/       # Pipeline stages, state machine, Temporal integration
│   │   ├── repositories/       # Data access layer
│   │   ├── schemas/            # Pydantic v2 request/response schemas
│   │   ├── services/           # Business logic (LLM router, prompt service, export, dashboard)
│   │   ├── utils/              # ID generation, JSON repair, retry, time helpers
│   │   ├── validators/         # OPA/Rego and Terraform syntax validation
│   │   ├── workers/            # Celery task definitions
│   │   └── main.py             # FastAPI app entry point
│   ├── requirements.txt
│   └── .env.example
│
├── src/                        # Next.js 15 frontend
│   ├── app/
│   │   ├── dashboard/          # Main dashboard (incidents, metrics, review queue)
│   │   ├── incidents/
│   │   │   ├── [id]/           # Incident detail + artifact viewer
│   │   │   └── new/            # New incident submission form
│   │   ├── analytics/          # Charts: risk by service, artifact breakdown
│   │   ├── workflow/           # Pipeline visualizer
│   │   └── layout.tsx          # Root layout + providers
│   ├── components/
│   │   ├── dashboard/          # StatCard, MTTGGauge, RiskTrendChart, GuardrailReviewQueue
│   │   ├── incident/           # ProviderSelector, SeveritySelector, UploadDropzone
│   │   ├── layout/             # Sidebar, TopNav, Providers (React Query + toasts)
│   │   ├── shared/             # PipelineStepper (single source of truth), EmptyState, ErrorState
│   │   ├── ui/                 # Button, Input, Textarea, Dialog, Tabs, CodeBlock, Tooltip…
│   │   ├── workflow/           # PipelineNode, StageDetail, IncidentSidebar
│   │   └── landing/            # Marketing page sections
│   ├── lib/
│   │   ├── api.ts              # Typed API layer (mock + real backend)
│   │   ├── hooks/              # useIncidents, useWorkflowRun, useDashboardStats
│   │   ├── mock-data.ts        # Realistic sample incidents, artifacts, runs
│   │   ├── store.ts            # Zustand UI state
│   │   └── types.ts            # Shared TypeScript types
│   └── app/globals.css         # Design system tokens + component classes
│
├── mlops/                      # Evaluation & regression
│   └── evaluation/
│       ├── golden_dataset/     # Hand-labeled test cases
│       ├── metrics.py          # DeepEval metric definitions
│       └── test_golden_dataset.py
│
├── .github/workflows/
│   └── eval_regression.yml     # CI: run eval gate on every PR
│
└── docker-compose.yml          # Full stack: API + frontend + Redis + Temporal
```

---

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### 1. Clone and set up

```bash
git clone https://github.com/YOUR_USERNAME/cirus.git
cd cirus
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate.bat
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# The defaults work out of the box — no API keys needed for mock mode
```

Start the API server:

```bash
uvicorn app.main:app --reload
```

API is live at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

### 3. Frontend

```bash
# From the project root
npm install
npm run dev
```

Frontend is live at `http://localhost:3000`

### 4. Submit a test incident

```bash
curl -X POST http://localhost:8000/api/v1/incidents/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-12345" \
  -d '{
    "raw_text": "P1 Incident — payments-api 503 rate 94%\n\nRDS CPU maxed at 99%. New DB migration in v2.4.1 added missing index on transactions table, causing full table scans under production load.\n\nTimeline:\n14:10 - Deployment completed\n14:12 - CloudWatch alarm fired\n14:22 - Rollback initiated\n14:31 - Service recovered",
    "severity": "P1",
    "provider": "AWS",
    "selected_artifacts": ["rca", "runbook", "policy", "iac"]
  }'
```

---

## Configuration

All configuration is via environment variables. Copy `backend/.env.example` to `backend/.env`.

### LLM providers

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `mock` · `openai` · `anthropic` · `groq` · `featherless` |
| `OPENAI_API_KEY` | Required when `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | Required when `LLM_PROVIDER=anthropic` |
| `GROQ_API_KEY` | Required when `LLM_PROVIDER=groq` |
| `FEATHERLESS_API_KEY` | Required when `LLM_PROVIDER=featherless` |

### Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./cirus_dev.db` | SQLite for dev, PostgreSQL for prod |
| `ENVIRONMENT` | `development` | `development` auto-creates tables on startup |

### Optional services

| Variable | Default | Description |
|---|---|---|
| `FIRECRAWL_ENABLED` | `false` | Enable web scraping for context enrichment |
| `WOLFRAM_ENABLED` | `false` | Enable Wolfram Alpha for quantitative analysis |
| `CELERY_ENABLED` | `false` | Use Celery + Redis for async task processing |

### Frontend

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |
| `NEXT_PUBLIC_API_KEY` | `dev-api-key-12345` | API key sent with every request |
| `NEXT_PUBLIC_USE_MOCKS` | *(unset)* | Set to `true` to use in-memory mock data only |

---

## Running with Docker

```bash
docker compose up --build
```

Services:
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Redis: `localhost:6379`

---

## API reference

Full interactive docs available at `http://localhost:8000/docs` when the server is running.

### Core endpoints

```
POST   /api/v1/incidents/              Submit a new incident
GET    /api/v1/incidents/              List all incidents
GET    /api/v1/incidents/{id}          Get incident detail + timeline
PATCH  /api/v1/incidents/{id}          Update title, severity, provider, tags
DELETE /api/v1/incidents/{id}          Delete an incident

GET    /api/v1/artifacts/{incident_id}              Get all artifacts
POST   /api/v1/artifacts/{incident_id}/regenerate   Regenerate a single artifact type

GET    /api/v1/runs/{run_id}                        Get workflow run detail
GET    /api/v1/runs/by-incident/{incident_id}       Get run for an incident

GET    /api/v1/dashboard/stats                      Dashboard KPI aggregation

POST   /api/v1/knowledge/               Upload knowledge base document
GET    /api/v1/exports/{incident_id}    Export all artifacts as ZIP
```

### Authentication

All endpoints require the `X-API-Key` header. Configure allowed keys via `ALLOWED_API_KEYS` (comma-separated list).

---

## Development

### Running the eval suite

```bash
cd backend
pytest mlops/evaluation/test_golden_dataset.py -v
```

The CI pipeline (`eval_regression.yml`) runs this on every PR and blocks merges if eval scores drop below threshold.

### Adding a new LLM provider

1. Add your provider config to `backend/app/core/config.py`
2. Implement the provider case in `backend/app/services/llm_router.py`
3. Add the env vars to `.env.example`

### Adding a new artifact type

1. Add the type to `ArtifactType` literal in `backend/app/models/artifact.py` and `src/lib/types.ts`
2. Add a prompt template in `backend/app/services/prompt_service.py`
3. Add the stage output handler in `backend/app/orchestrator/stages.py`
4. Add a tab and renderer in `src/components/ArtifactTabs.tsx`

---

## Roadmap

- [ ] GitHub PR integration — auto-open PRs with generated IaC patches
- [ ] Slack / PagerDuty webhook ingestion
- [ ] SSO / multi-tenant workspace support
- [ ] Vector store for historical incident similarity search
- [ ] Temporal workflow orchestration (infrastructure in place, needs cloud setup)
- [ ] SARIF output for security scanner integration
- [ ] Automatic severity escalation based on risk delta

---

## Tech stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com) — async REST API
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org) — async ORM with aiosqlite / asyncpg
- [Pydantic v2](https://docs.pydantic.dev) — request/response validation
- [Temporalio](https://temporal.io) — durable workflow orchestration (optional)
- [Celery](https://celeryproject.org) — async task queue (optional)
- [DeepEval](https://deepeval.com) — LLM evaluation framework

**Frontend**
- [Next.js 15](https://nextjs.org) — React framework with App Router
- [TanStack Query](https://tanstack.com/query) — server state management
- [Framer Motion](https://www.framer.com/motion) — animations
- [Recharts](https://recharts.org) — composable chart library
- [Zustand](https://zustand-demo.pmnd.rs) — client state management
- [Base UI](https://base-ui.com) — unstyled accessible UI primitives

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit your changes following [Conventional Commits](https://www.conventionalcommits.org)
4. Open a PR — the eval regression gate runs automatically

---

## License

MIT — see [LICENSE](LICENSE) for details.
