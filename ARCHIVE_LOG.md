# CIRUS — Archive Log

This file records all files and directories moved out of the active codebase into `_archive/`.

**Safety Policy:** Nothing was deleted. All files, historical artifacts, and one-off scripts are preserved in `_archive/` so that no context or historical experiments are lost.

---

## Files and Folders Moved to `_archive/`

| Original Location | Moved Location | Type | Size | Reason for Archiving |
|-------------------|----------------|------|------|----------------------|
| `temporal.exe` | `_archive/temporal.exe` | Binary executable | ~141 MB | Windows Temporal development server executable placed in repo root. Unneeded for core Python/FastAPI backend and Next.js frontend; should not clutter root directory. |
| `temporal.zip` | `_archive/temporal.zip` | Compressed Archive | ~42 MB | Duplicate zip archive containing Temporal server distribution. |
| `temporal2.zip` | `_archive/temporal2.zip` | Compressed Archive | ~42 MB | Duplicate zip archive containing Temporal server distribution. |
| `temporal3.zip` | `_archive/temporal3.zip` | Compressed Archive | ~28 MB | Duplicate zip archive containing Temporal CLI distribution. |
| `temporal4.zip` | `_archive/temporal4.zip` | Compressed Archive | ~42 MB | Duplicate zip archive containing Temporal server distribution. |
| `temporal_bin/` | `_archive/temporal_bin/` | Extracted Directory | Multi-file | Extracted binaries from early manual Temporal testing. |
| `temporal_bin2/` | `_archive/temporal_bin2/` | Extracted Directory | Multi-file | Secondary extracted binaries from early manual Temporal testing. |
| `temporal_cli/` | `_archive/temporal_cli/` | Extracted Directory | Multi-file | Extracted Temporal CLI directory. |
| `exports/` | `_archive/exports/` | Directory | Data files | Early incident export dump folder; not referenced in pipeline execution. |
| `backend/test_incident.py` | `_archive/test_incident.py` | Python Script | ~1.6 KB | Early one-off manual test script using the `requests` library. Replaced by official automated pytest suite in `backend/tests/`. |
| `backend/trigger_manual.py` | `_archive/trigger_manual.py` | Python Script | ~1.6 KB | Early one-off manual Temporal workflow trigger script. Replaced by standard FastAPI API endpoints (`POST /api/v1/incidents/`). |

---

## Verification

After archiving these files:
- All 29 automated tests in `backend/tests/` passed with 0 failures.
- Frontend Next.js production build succeeded with 0 errors across all 8 routes.
