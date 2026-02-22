"""
SQLite-backed session store using aiosqlite.
Stores: manifests, markers, qc_status snapshots, and findings.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

DB_PATH = Path("qc_sessions.db")


class SessionStore:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._db: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def _create_tables(self) -> None:
        assert self._db
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                lab_id TEXT,
                rig_id TEXT,
                modality TEXT,
                manifest_json TEXT NOT NULL,
                started_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS markers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                t_mono_ns INTEGER NOT NULL,
                marker_type TEXT NOT NULL,
                value TEXT,
                meta_json TEXT
            );

            CREATE TABLE IF NOT EXISTS qc_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                t_eval_mono_ns INTEGER NOT NULL,
                state TEXT NOT NULL,
                risk_score REAL NOT NULL,
                findings_json TEXT,
                recorded_at TEXT NOT NULL
            );
            """
        )
        await self._db.commit()

    async def upsert_session(self, manifest: dict[str, Any]) -> None:
        assert self._db
        await self._db.execute(
            """
            INSERT OR REPLACE INTO sessions
                (session_id, lab_id, rig_id, modality, manifest_json, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                manifest.get("session_id"),
                manifest.get("lab_id"),
                manifest.get("rig_id"),
                manifest.get("modality"),
                json.dumps(manifest),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._db.commit()

    async def insert_marker(
        self,
        session_id: str,
        t_mono_ns: int,
        marker_type: str,
        value: str = "",
        meta: dict | None = None,
    ) -> None:
        assert self._db
        await self._db.execute(
            """
            INSERT INTO markers (session_id, t_mono_ns, marker_type, value, meta_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, t_mono_ns, marker_type, value, json.dumps(meta or {})),
        )
        await self._db.commit()

    async def insert_qc_status(
        self,
        session_id: str,
        t_eval_mono_ns: int,
        state: str,
        risk_score: float,
        findings: list[dict],
    ) -> None:
        assert self._db
        await self._db.execute(
            """
            INSERT INTO qc_status
                (session_id, t_eval_mono_ns, state, risk_score, findings_json, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                t_eval_mono_ns,
                state,
                risk_score,
                json.dumps(findings),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._db.commit()

    async def get_sessions(
        self, lab_id: str | None = None
    ) -> list[dict[str, Any]]:
        assert self._db
        if lab_id:
            async with self._db.execute(
                "SELECT * FROM sessions WHERE lab_id=? ORDER BY started_at DESC",
                (lab_id,),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with self._db.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC"
            ) as cur:
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def get_latest_qc_status(
        self, session_id: str
    ) -> dict[str, Any] | None:
        assert self._db
        async with self._db.execute(
            """
            SELECT * FROM qc_status WHERE session_id=?
            ORDER BY t_eval_mono_ns DESC LIMIT 1
            """,
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None
