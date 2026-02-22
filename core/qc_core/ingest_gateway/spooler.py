"""
Spooler – writes session artifacts to disk for replay and audit.

Directory layout:
  spool/{session_id}/
    manifest.json
    markers.jsonl
    qc_status.jsonl
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SPOOL_ROOT = Path("spool")


class Spooler:
    def __init__(self, root: str | Path = SPOOL_ROOT):
        self.root = Path(root)

    def _session_dir(self, session_id: str) -> Path:
        d = self.root / session_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write_manifest(self, session_id: str, manifest: dict[str, Any]) -> None:
        path = self._session_dir(session_id) / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2))

    def append_marker(self, session_id: str, event: dict[str, Any]) -> None:
        path = self._session_dir(session_id) / "markers.jsonl"
        with path.open("a") as f:
            f.write(json.dumps(event) + "\n")

    def append_qc_status(self, session_id: str, status: dict[str, Any]) -> None:
        path = self._session_dir(session_id) / "qc_status.jsonl"
        with path.open("a") as f:
            f.write(json.dumps(status) + "\n")
