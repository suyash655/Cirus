"""CIRUS — Service: Export artifacts to Markdown, JSON, or ZIP."""
from __future__ import annotations

import io
import json
import os
import zipfile
from datetime import datetime, timezone
from typing import Literal

from app.core.config import settings
from app.core.errors import ExportError
from app.core.logging import get_logger

log = get_logger(__name__)

ExportFormat = Literal["markdown", "json", "zip"]


class ExportService:
    def __init__(self) -> None:
        os.makedirs(settings.EXPORT_DIR, exist_ok=True)

    def export_as_json(self, incident_id: str, artifact_set: dict) -> bytes:
        try:
            payload = {
                "incident_id": incident_id,
                "exported_at": datetime.now(tz=timezone.utc).isoformat(),
                "artifacts": artifact_set,
            }
            return json.dumps(payload, indent=2, default=str).encode("utf-8")
        except Exception as e:
            raise ExportError(f"JSON export failed: {e}")

    def export_as_markdown(self, incident_id: str, artifact_set: dict) -> bytes:
        try:
            lines = [
                f"# CIRUS Incident Report: {incident_id}",
                f"\n_Exported: {datetime.now(tz=timezone.utc).isoformat()}_\n",
            ]
            for art_type, artifact in artifact_set.items():
                if not artifact:
                    continue
                lines.append(f"\n## {art_type.upper()}\n")
                content = artifact.get("content", {})
                for key, value in content.items():
                    if key == "type":
                        continue
                    lines.append(f"### {key.replace('_', ' ').title()}\n")
                    if isinstance(value, list):
                        for item in value:
                            lines.append(f"- {item}\n")
                    elif isinstance(value, dict):
                        lines.append(f"```json\n{json.dumps(value, indent=2)}\n```\n")
                    elif isinstance(value, str) and len(value) > 80:
                        lines.append(f"```\n{value}\n```\n")
                    else:
                        lines.append(f"{value}\n")
            return "\n".join(lines).encode("utf-8")
        except Exception as e:
            raise ExportError(f"Markdown export failed: {e}")

    def export_as_zip(self, incident_id: str, artifact_set: dict) -> bytes:
        try:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add JSON export
                json_bytes = self.export_as_json(incident_id, artifact_set)
                zf.writestr(f"{incident_id}/full_report.json", json_bytes)

                # Add markdown export
                md_bytes = self.export_as_markdown(incident_id, artifact_set)
                zf.writestr(f"{incident_id}/report.md", md_bytes)

                # Add individual artifact files
                for art_type, artifact in artifact_set.items():
                    if not artifact:
                        continue
                    content = artifact.get("content", {})
                    # Embed code artifacts as their native format
                    code = content.get("code") or content.get("diff") or content.get("full_patch")
                    if code:
                        ext = _code_extension(art_type, content)
                        zf.writestr(f"{incident_id}/{art_type}{ext}", code)

            return buffer.getvalue()
        except Exception as e:
            raise ExportError(f"ZIP export failed: {e}")


def _code_extension(art_type: str, content: dict) -> str:
    if art_type == "policy":
        lang = content.get("language", "rego")
        return f".{lang}"
    if art_type == "iac":
        tool = content.get("tool", "terraform")
        return ".tf" if tool == "terraform" else ".yaml"
    if art_type == "regression":
        fw = content.get("framework", "pytest")
        return ".py" if fw == "pytest" else ".test.js"
    return ".txt"
