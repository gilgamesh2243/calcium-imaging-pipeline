"""
FastAPI REST routes for sessions, QC status, and health.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from qc_core.storage.session_store import SessionStore

router = APIRouter()
_store: SessionStore | None = None


def set_store(store: SessionStore) -> None:
    global _store
    _store = store


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/sessions")
async def list_sessions(lab_id: str | None = None) -> list[dict[str, Any]]:
    if _store is None:
        return []
    return await _store.get_sessions(lab_id=lab_id)


@router.get("/sessions/{session_id}/status")
async def session_status(session_id: str) -> dict[str, Any]:
    if _store is None:
        raise HTTPException(status_code=503, detail="Store not ready")
    status = await _store.get_latest_qc_status(session_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return status


@router.get("/sessions/{session_id}/manifest")
async def session_manifest(session_id: str) -> dict[str, Any]:
    spool_path = Path("spool") / session_id / "manifest.json"
    if not spool_path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    return json.loads(spool_path.read_text())
