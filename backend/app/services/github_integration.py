"""CIRUS — Service: GitHub integration for opening validated Pull Requests.

AUTH DECISION: GitHub App over PAT
-----------------------------------
We use a GitHub App (not a Personal Access Token) for the following reasons:

1. LEAST PRIVILEGE: The App only requests `pull_requests:write` + `contents:write`
   (to create branches). A PAT with `repo` scope grants write access to ALL
   repositories the user can see — that's catastrophic if a token leaks.

2. EPHEMERAL TOKENS: GitHub App installation tokens expire after 1 hour.
   A leaked App token is useless within the hour. A leaked PAT is valid
   until manually revoked (often days or never).

3. IDENTITY: The App acts as `cirus-bot[bot]`, not a human account. This means
   PRs are clearly machine-authored, auditable separately from human commits,
   and the bot doesn't break if an employee leaves.

4. REPO-SCOPED: The App installation can be limited to a specific repository.
   Zero blast radius outside the target infra repo.

REQUIRED GITHUB APP PERMISSIONS:
  Repository permissions:
    - Contents: Read and write (to create branches + push files)
    - Pull requests: Read and write (to open PRs)
    - Metadata: Read (required baseline)

REQUIRED ENV VARS:
  GITHUB_APP_ID         — numeric App ID from the App settings page
  GITHUB_APP_PRIVATE_KEY — PEM private key (newlines as \\n in .env)
  GITHUB_INSTALLATION_ID — Installation ID for the target org/repo
  GITHUB_TARGET_REPO    — "owner/repo-name" of the infra repo

DUPLICATE PR HANDLING:
  Before opening a PR, we search for existing open PRs with the same
  incident ID in the title. If found, we update the existing PR body
  rather than opening a duplicate.

FAILURE PATHS:
  - Eval gate failed: No PR opened. Incident status set to "error".
    Surface: incident detail page shows eval gate failure with specific issues.
  - GitHub auth failed: No PR opened. Logged as ERROR. Incident status
    set to "ready" (artifacts still available) with a github_pr_failed flag.
  - Target repo already has open PR for this incident: PR body updated, not duplicated.
  - Branch already exists: Use existing branch, force-push the new content.
"""
from __future__ import annotations

import base64
import logging
import os
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


def _generate_jwt(app_id: str, private_key_pem: str) -> str:
    """Generate a GitHub App JWT for authenticating as the App itself."""
    import jwt  # PyJWT

    now = int(time.time())
    payload = {
        "iat": now - 60,   # issued 60s ago (clock skew tolerance)
        "exp": now + 600,  # expires in 10 minutes
        "iss": app_id,
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


def _get_installation_token(app_id: str, private_key_pem: str, installation_id: str) -> str:
    """Exchange App JWT for a short-lived installation access token (1h expiry)."""
    import urllib.request
    import json

    jwt_token = _generate_jwt(app_id, private_key_pem)
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"

    req = urllib.request.Request(url, method="POST")
    req.add_header("Authorization", f"Bearer {jwt_token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
        return data["token"]


def _get_github_client():
    """
    Build an authenticated PyGitHub client using GitHub App auth.
    Falls back to PAT (GITHUB_TOKEN) for local development convenience.
    """
    from github import Github, Auth

    from app.core.config import settings

    app_id = getattr(settings, "GITHUB_APP_ID", "")
    private_key = getattr(settings, "GITHUB_APP_PRIVATE_KEY", "").replace("\\n", "\n")
    installation_id = getattr(settings, "GITHUB_INSTALLATION_ID", "")

    if app_id and private_key and installation_id:
        try:
            token = _get_installation_token(app_id, private_key, installation_id)
            log.info("Authenticated with GitHub App installation token")
            return Github(auth=Auth.Token(token))
        except Exception as e:
            log.error(f"GitHub App auth failed: {e}")
            raise

    # Fallback: PAT (dev only — not for production)
    pat = getattr(settings, "GITHUB_TOKEN", "")
    if pat:
        log.warning("Using GitHub PAT — GitHub App is strongly preferred for production")
        return Github(auth=Auth.Token(pat))

    raise RuntimeError(
        "No GitHub credentials configured. Set GITHUB_APP_ID + GITHUB_APP_PRIVATE_KEY + "
        "GITHUB_INSTALLATION_ID (preferred) or GITHUB_TOKEN (dev only)."
    )


# ── PR Content Generation ────────────────────────────────────────────────────

def _build_pr_title(incident_reference: str) -> str:
    return f"[CIRUS] {incident_reference}: automated prevention artifacts"


def _build_pr_body(
    incident_reference: str,
    cirus_incident_id: str,
    rca_summary: str,
    artifacts_generated: List[str],
    eval_scores: Dict[str, float],
    postmortem_url: Optional[str] = None,
) -> str:
    scores_table = "\n".join(
        f"| {k} | {v:.2f} |" for k, v in eval_scores.items()
    ) if eval_scores else "| N/A | — |"

    artifacts_list = "\n".join(f"- `{a}`" for a in artifacts_generated)

    return f"""## 🔒 CIRUS Prevention Artifacts — {incident_reference}

This Pull Request was automatically generated by [CIRUS](https://github.com/your-org/cirus)
in response to the post-mortem completion of **{incident_reference}**.

---

### Root Cause Analysis Summary

{rca_summary or "_RCA summary not available._"}

---

### Generated Artifacts

{artifacts_list}

---

### Quality Gate Results

| Metric | Score |
|--------|-------|
{scores_table}

All artifacts passed the CIRUS evaluation gate before this PR was opened.

---

### Source

- **Incident reference**: `{incident_reference}`
- **CIRUS incident ID**: `{cirus_incident_id}`
{f"- **Post-mortem**: {postmortem_url}" if postmortem_url else ""}

---

> **Review checklist**
> - [ ] Rego policy addresses the specific misconfiguration described in the RCA
> - [ ] Terraform patch is idempotent (safe to apply to existing infrastructure)
> - [ ] Alert rule thresholds reviewed for false-positive rate
> - [ ] Runbook reviewed by on-call team

_Opened automatically by CIRUS. Do not merge without engineering review._
"""


# ── Main PR creation function ────────────────────────────────────────────────

async def open_prevention_pr(
    incident_reference: str,     # e.g. "INC-104"
    cirus_incident_id: str,
    artifacts: Dict[str, str],   # {"policy": "<rego code>", "iac": "<hcl>", ...}
    rca_summary: str,
    eval_scores: Dict[str, float],
    postmortem_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Open (or update) a GitHub PR with the validated prevention artifacts.

    Returns:
      {"pr_url": str, "pr_number": int, "action": "created"|"updated"|"skipped"}

    Failure paths:
    1. GitHub auth failure → raises exception (caller sets incident status)
    2. Duplicate PR → updates existing PR body, returns action="updated"
    3. Branch creation failure → logs error, re-raises
    """
    from app.core.config import settings

    target_repo = getattr(settings, "GITHUB_TARGET_REPO", "")
    if not target_repo:
        log.warning("GITHUB_TARGET_REPO not configured — skipping PR creation")
        return {"action": "skipped", "reason": "GITHUB_TARGET_REPO not set"}

    try:
        gh = _get_github_client()
        repo = gh.get_repo(target_repo)
    except Exception as e:
        log.error(f"GitHub authentication failed: {e}")
        raise RuntimeError(f"GitHub auth failed: {e}") from e

    pr_title = _build_pr_title(incident_reference)
    branch_name = f"cirus/{incident_reference.lower().replace('-', '')}-prevention"

    # ── Check for duplicate open PRs ─────────────────────────────────────────
    open_prs = repo.get_pulls(state="open", head=branch_name)
    existing_pr = None
    for pr in open_prs:
        if incident_reference in pr.title:
            existing_pr = pr
            break

    if not existing_pr:
        # Also search by title across all open PRs (branch may differ)
        all_open = repo.get_pulls(state="open")
        for pr in all_open:
            if incident_reference in pr.title:
                existing_pr = pr
                break

    # ── Build file tree for the PR ────────────────────────────────────────────
    files_to_create: Dict[str, str] = {}

    if "policy" in artifacts and artifacts["policy"]:
        policy_code = artifacts["policy"]
        if isinstance(policy_code, dict):
            policy_code = policy_code.get("code", str(policy_code))
        files_to_create[f"policies/{incident_reference.lower()}/prevent.rego"] = policy_code

    if "iac" in artifacts and artifacts["iac"]:
        iac_code = artifacts["iac"]
        if isinstance(iac_code, dict):
            iac_code = iac_code.get("fullPatch") or iac_code.get("diff") or str(iac_code)
        files_to_create[f"terraform/patches/{incident_reference.lower()}/fix.tf"] = iac_code

    if "rca" in artifacts and artifacts["rca"]:
        rca = artifacts["rca"]
        if isinstance(rca, dict):
            rca_text = f"# RCA: {incident_reference}\n\n{rca.get('executiveSummary', '')}\n\n{rca.get('details', '')}"
        else:
            rca_text = str(rca)
        files_to_create[f"docs/rca/{incident_reference.lower()}.md"] = rca_text

    if "runbook" in artifacts and artifacts["runbook"]:
        runbook = artifacts["runbook"]
        if isinstance(runbook, dict):
            steps = runbook.get("steps", [])
            runbook_text = f"# Runbook: {incident_reference}\n\n" + "\n".join(
                f"## Step {s.get('id', i+1)}: {s.get('title', '')}\n\n{s.get('description', '')}"
                for i, s in enumerate(steps)
            )
        else:
            runbook_text = str(runbook)
        files_to_create[f"runbooks/{incident_reference.lower()}.md"] = runbook_text

    pr_body = _build_pr_body(
        incident_reference=incident_reference,
        cirus_incident_id=cirus_incident_id,
        rca_summary=rca_summary,
        artifacts_generated=list(artifacts.keys()),
        eval_scores=eval_scores,
        postmortem_url=postmortem_url,
    )

    if existing_pr:
        # ── Update existing PR (dedup) ────────────────────────────────────────
        log.info(f"Updating existing PR #{existing_pr.number} for {incident_reference}")
        existing_pr.edit(body=pr_body)
        # Also update files on the existing branch
        _push_files_to_branch(repo, branch_name, files_to_create, incident_reference, create_branch=False)
        return {
            "action": "updated",
            "pr_url": existing_pr.html_url,
            "pr_number": existing_pr.number,
        }

    # ── Create new branch ─────────────────────────────────────────────────────
    default_branch = repo.default_branch
    base_sha = repo.get_branch(default_branch).commit.sha

    try:
        repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
        log.info(f"Created branch {branch_name} from {default_branch}@{base_sha[:7]}")
    except Exception as e:
        if "already exists" in str(e).lower():
            log.info(f"Branch {branch_name} already exists, using existing branch")
        else:
            raise

    # ── Push files ────────────────────────────────────────────────────────────
    _push_files_to_branch(repo, branch_name, files_to_create, incident_reference, create_branch=False)

    # ── Open PR ───────────────────────────────────────────────────────────────
    pr = repo.create_pull(
        title=pr_title,
        body=pr_body,
        head=branch_name,
        base=default_branch,
        draft=False,
    )

    # Add CIRUS label if it exists
    try:
        cirus_label = repo.get_label("cirus-automated")
        pr.add_to_labels(cirus_label)
    except Exception:
        pass  # Label doesn't exist — skip silently

    log.info(f"Opened PR #{pr.number} for {incident_reference}: {pr.html_url}")
    return {
        "action": "created",
        "pr_url": pr.html_url,
        "pr_number": pr.number,
    }


def _push_files_to_branch(
    repo,
    branch_name: str,
    files: Dict[str, str],
    incident_reference: str,
    create_branch: bool = False,
) -> None:
    """Push or update files on a branch."""
    for file_path, content in files.items():
        commit_message = f"chore: CIRUS prevention artifact for {incident_reference} — {file_path}"
        try:
            # Try to get existing file (for update)
            existing = repo.get_contents(file_path, ref=branch_name)
            repo.update_file(
                file_path,
                commit_message,
                content,
                existing.sha,
                branch=branch_name,
            )
            log.debug(f"Updated {file_path} on {branch_name}")
        except Exception:
            # File doesn't exist — create it
            try:
                repo.create_file(
                    file_path,
                    commit_message,
                    content,
                    branch=branch_name,
                )
                log.debug(f"Created {file_path} on {branch_name}")
            except Exception as e:
                log.warning(f"Failed to push {file_path}: {e}")
