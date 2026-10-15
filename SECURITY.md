# Security Policy

## ⚠️ Intentional Dev Credentials (Read This First)

CIRUS ships with a **hardcoded development API key** for local demo purposes:

```
dev-api-key-12345
```

This is **intentional and documented**. It is:
- Used only when `ENVIRONMENT=development` or `MODE=mock`
- Listed in `.env.example` as the default value for `ALLOWED_API_KEYS`
- Never valid against any external service — it only authenticates requests
  to your locally-running FastAPI server
- Meaningless without network access to your machine

**GitHub secret scanning alert?** This is a false positive. The key exists
exclusively to let `git clone && docker compose up` work with zero config.
See `backend/.env.example` for the full credential surface area.

---

## Credentials to Rotate Before Any Real Deployment

Before deploying CIRUS in any non-local environment, **you must rotate**:

| Variable | Default Dev Value | Risk if Leaked |
|---|---|---|
| `ALLOWED_API_KEYS` | `dev-api-key-12345` | Unauthorized pipeline triggers |
| `OPENAI_API_KEY` | *(empty)* | Billing exposure |
| `ANTHROPIC_API_KEY` | *(empty)* | Billing exposure |
| `GROQ_API_KEY` | *(empty)* | Billing exposure |
| `GITHUB_APP_PRIVATE_KEY` | *(empty)* | Unauthorized repo access |
| `GITHUB_INSTALLATION_ID` | *(empty)* | Unauthorized PR creation |
| `LANGFUSE_SECRET_KEY` | *(empty)* | Observability data exposure |
| `FIRECRAWL_API_KEY` | *(empty)* | Billing exposure |
| `WOLFRAM_APP_ID` | *(empty)* | Billing exposure |
| `INCIDENT_IO_WEBHOOK_SECRET` | *(empty)* | Spoofed webhook payloads |

Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret
Manager) for all production credentials. Never commit a populated `.env` file.

---

## Authentication Architecture

### API Authentication (current)
All API endpoints require an `X-API-Key` header. The key is validated against
`ALLOWED_API_KEYS` (comma-separated list in env). This is suitable for:
- Internal tooling with network-level access control
- CI/CD pipelines with secrets management

### GitHub Integration Security
The GitHub integration uses a **GitHub App** (not a Personal Access Token):
- Installation tokens expire after **1 hour** — a leaked token is useless within the hour
- The App only requests `pull_requests:write` + `contents:write` on a single repo
- Acts as `cirus-bot[bot]`, not a human account — PRs are auditable separately

See [`backend/app/services/github_integration.py`](backend/app/services/github_integration.py)
for the full security rationale in the module docstring.

### Webhook Verification
All webhooks (incident.io, future Slack/PagerDuty) are verified via
**HMAC-SHA256** signature before any processing. Requests without a valid
signature receive `401 Unauthorized`. Replay attacks are prevented by a
±5-minute timestamp tolerance window.

See [`backend/app/services/incident_io_webhook.py`](backend/app/services/incident_io_webhook.py).

---

## Supported Versions

| Version | Supported |
|---|---|
| `main` branch | ✅ Yes |
| Any tagged release | ✅ Yes |
| Forks / older branches | ❌ Not supported |

---

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a vulnerability:

1. **GitHub Private Vulnerability Reporting** (preferred): Use the
   [Security Advisories](../../security/advisories/new) feature in this
   repository to report privately.

2. **Response timeline:**
   - Acknowledgment within **48 hours**
   - Initial assessment within **7 days**
   - Fix or mitigation plan within **30 days** for confirmed issues

3. **Scope:** Vulnerabilities in the CIRUS application code itself.
   Vulnerabilities in upstream dependencies should be reported to their
   respective maintainers.

---

## Known Security Limitations (by Design)

These are intentional trade-offs in the current version, not vulnerabilities:

- **Static API keys** — JWT-based auth with workspace claims is on the roadmap
  (`feat/jwt-auth`). The current static key model is appropriate for
  single-tenant internal deployment.
- **SQLite in dev mode** — SQLite has no user-level auth. The dev database
  contains no real incident data when running with `MODE=mock`.
- **LLM output is not sanitized for XSS** — Generated artifacts are displayed
  in a `<CodeBlock>` component, not `dangerouslySetInnerHTML`. The frontend
  renders artifact text as plain text in syntax-highlighted code blocks.
