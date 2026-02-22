"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Session } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [labFilter, setLabFilter] = useState("");

  useEffect(() => {
    const url = labFilter
      ? `${API_BASE}/sessions?lab_id=${encodeURIComponent(labFilter)}`
      : `${API_BASE}/sessions`;

    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setSessions(data as Session[]);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Unknown error");
        setLoading(false);
      });
  }, [labFilter]);

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Sessions</h1>
        <Link href="/live" className="text-sm text-blue-400 hover:underline">
          ← Live session
        </Link>
      </div>

      <div className="mb-4">
        <input
          type="text"
          placeholder="Filter by lab ID…"
          value={labFilter}
          onChange={(e) => setLabFilter(e.target.value)}
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm w-64 focus:outline-none focus:border-blue-500"
        />
      </div>

      {loading && <p className="text-gray-500">Loading…</p>}
      {error && (
        <p className="text-red-400 text-sm">
          Could not load sessions: {error}. Is qc-core running?
        </p>
      )}

      {!loading && !error && sessions.length === 0 && (
        <p className="text-gray-500 italic">No sessions found.</p>
      )}

      <div className="space-y-3">
        {sessions.map((s) => (
          <div key={s.session_id} className="rounded-xl bg-gray-800 p-4 flex items-center justify-between">
            <div>
              <p className="font-mono text-sm font-semibold">{s.session_id}</p>
              <p className="text-gray-400 text-xs mt-0.5">
                {s.lab_id} / {s.rig_id} · {s.modality}
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">{new Date(s.started_at).toLocaleString()}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
