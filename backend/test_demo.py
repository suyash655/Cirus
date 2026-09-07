"""Demo incident test using httpx (no external deps needed)."""
import sys
import time
import httpx

API_URL = "http://localhost:8000/api/v1"
HEADERS = {"X-API-Key": "dev-api-key-12345"}

# All supported artifact types
ALL_ARTIFACTS = ["rca", "policy", "iac", "alerts", "runbook"]

payload = {
    "title": "AWS S3 Bucket Outage - Production",
    "raw_text": (
        "Critical incident: AWS S3 bucket 'prod-assets' became inaccessible at 14:32 UTC. "
        "All read/write operations returned 503 errors. The outage lasted approximately 30 minutes "
        "affecting the internal dashboard and customer-facing file uploads. Root cause appears to be "
        "an IAM policy misconfiguration applied during a routine access review. "
        "Services affected: dashboard, file-upload-service, report-generator."
    ),
    "severity": "P2",
    "provider": "AWS",
    "selected_artifacts": ALL_ARTIFACTS,  # <-- request all artifact types
}

def main():
    print("=" * 60)
    print("CIRUS Demo Incident Test")
    print("=" * 60)
    print(f"  Artifacts requested: {', '.join(ALL_ARTIFACTS)}")

    # ── 1. Submit incident ────────────────────────────────────────────────────────
    print("\n[1] Submitting incident...")
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        resp = client.post(f"{API_URL}/incidents/", json=payload, headers=HEADERS)

    if resp.status_code != 201:
        print(f"  FAILED: {resp.status_code} -- {resp.text}")
        sys.exit(1)

    incident = resp.json()
    assert "id" in incident, "Incident response missing 'id' field"
    assert incident["id"], "Incident ID is empty"
    incident_id = incident["id"]
    print(f"  OK Created incident ID: {incident_id}")
    print(f"  estimated_processing_ms: {incident.get('estimated_processing_ms')}")

    # ── 2. Poll for run completion (max 120s) ─────────────────────────────────────
    print("\n[2] Polling workflow run (max 120s)...")
    time.sleep(3)  # give asyncio.create_task a moment to kick off

    completed = False
    run_status = "unknown"
    run = {}
    for i in range(60):
        with httpx.Client(timeout=10) as client:
            res = client.get(f"{API_URL}/runs/by-incident/{incident_id}", headers=HEADERS)

        if res.status_code == 200:
            run = res.json()
            if run is None:
                print(f"  [{i*2:>3}s] Run not yet created, waiting...")
            else:
                run_status = run.get("status", "unknown")
                current_stage = run.get("current_stage", "--")
                elapsed = i * 2
                print(f"  [{elapsed:>3}s] Run status: {run_status:<12} | Stage: {current_stage}")
                if run_status in ("completed", "failed", "error"):
                    completed = True
                    print(f"\n  Workflow finished with status: {run_status}")
                    if run_status == "failed":
                        print(f"  Error: {run.get('error_message', 'unknown')}")
                    break
        elif res.status_code == 404:
            print(f"  [{i*2:>3}s] Run not yet created, waiting...")
        else:
            print(f"  Error fetching run: {res.status_code} -- {res.text}")
        time.sleep(2)

    if not completed:
        print("\n  WARNING: Timed out waiting for workflow to complete")
        assert False, "Workflow did not complete within the timeout"

    assert run_status == "completed", f"Workflow failed with status: {run_status}"

    # Validate workflow stages more thoroughly after completion
    assert "stages" in run, "Run response missing 'stages' field"
    assert isinstance(run["stages"], list), "Run stages should be a list"
    assert len(run["stages"]) > 0, "Run has no stages"

    # Check that critical stages completed successfully
    critical_stages = ["normalization", "root-cause-classification", "artifact-generation"]
    for stage in run["stages"]:
        stage_id = stage.get("id", "")
        stage_status = stage.get("status", "")
        if stage_id in critical_stages:
            assert stage_status == "completed", f"Critical stage {stage_id} did not complete: {stage_status}"
            # Check that critical stages have non-empty output
            if stage_id in ["normalization", "root-cause-classification"]:
                assert "output" in stage, f"Stage {stage_id} missing 'output' field"
                assert stage["output"], f"Stage {stage_id} has empty output"

    # ── 3. Fetch final incident state ─────────────────────────────────────────────
    print("\n[3] Final incident state...")
    with httpx.Client(timeout=10) as client:
        inc_res = client.get(f"{API_URL}/incidents/{incident_id}", headers=HEADERS)

    assert inc_res.status_code == 200, f"Failed to fetch incident: {inc_res.text}"
    data = inc_res.json()
    assert "id" in data, "Incident data missing 'id' field"
    assert "status" in data, "Incident data missing 'status' field"
    assert "severity" in data, "Incident data missing 'severity' field"
    assert "provider" in data, "Incident data missing 'provider' field"
    assert data["id"] == incident_id, f"Incident ID mismatch: expected {incident_id}, got {data['id']}"
    print(f"  Status  : {data.get('status')}")
    print(f"  Severity: {data.get('severity')}")
    print(f"  Provider: {data.get('provider')}")
    arts = data.get("artifacts", [])
    print(f"  Artifacts in incident: {len(arts)}")
    assert data.get('status') == 'ready', f"Incident status is not ready: {data.get('status')}"
    assert data.get('severity') not in (None, "", "unknown"), f"Incident severity is invalid: {data.get('severity')}"
    assert data.get('provider') not in (None, "", "unknown"), f"Incident provider is invalid: {data.get('provider')}"

    # ── 4. Fetch artifact set (correct endpoint: /artifacts/{incident_id}) ────────
    print("\n[4] Fetching artifact set...")
    with httpx.Client(timeout=10) as client:
        art_res = client.get(f"{API_URL}/artifacts/{incident_id}", headers=HEADERS)

    assert art_res.status_code == 200, f"Could not fetch artifact set: {art_res.text}"
    artifact_set = art_res.json()
    assert isinstance(artifact_set, dict), "Artifact set should be a dictionary"
    print(f"  Artifact set keys: {list(artifact_set.keys())}")
    found = 0
    for atype, artifact in artifact_set.items():
        if artifact is not None:
            assert isinstance(artifact, dict), f"Artifact {atype} should be a dictionary"
            assert "content" in artifact, f"Artifact {atype} missing 'content' field"
            assert artifact["content"], f"Artifact {atype} has empty content"
            found += 1
            content_preview = str(artifact.get("content", ""))[:150].replace("\n", " ")
            print(f"\n  [{atype}] (version {artifact.get('version', '?')})")
            print(f"    Preview: {content_preview}...")
    print(f"\n  Total artifacts with content: {found}/{len(artifact_set)}")

    assert found > 0, "No artifacts were successfully generated"
    assert found == len(ALL_ARTIFACTS), f"Expected {len(ALL_ARTIFACTS)} artifacts, but found {found}"

    print("\n" + "=" * 60)
    print("Test complete! All assertions passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
