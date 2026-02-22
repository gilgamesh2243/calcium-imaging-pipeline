"use client";

import { useQCWebSocket } from "@/lib/useQCWebSocket";
import { StatusBadge } from "@/components/StatusBadge";
import { FindingsPanel } from "@/components/FindingsPanel";
import type { QCState } from "@/lib/types";

const WS_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/qc")
    : "ws://localhost:8000/ws/qc";

export default function LivePage() {
  const { status, connected } = useQCWebSocket(WS_URL);

  const state: QCState = status?.state ?? "UNKNOWN";
  const riskPct = status ? Math.round(status.risk_score * 100) : null;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Live Session</h1>
          {status && (
            <p className="text-gray-400 text-sm mt-0.5">
              Session: <span className="font-mono">{status.session_id}</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`h-2.5 w-2.5 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-gray-600"}`}
          />
          <span className="text-sm text-gray-400">{connected ? "Connected" : "Disconnected"}</span>
        </div>
      </div>

      {/* Status + risk */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="rounded-xl bg-gray-800 p-5">
          <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">QC State</p>
          <StatusBadge state={state} />
        </div>
        <div className="rounded-xl bg-gray-800 p-5">
          <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">Risk Score</p>
          {riskPct !== null ? (
            <>
              <p className="text-3xl font-bold">{riskPct}%</p>
              <div className="mt-2 h-2 w-full rounded-full bg-gray-700">
                <div
                  className={`h-2 rounded-full transition-all ${
                    riskPct > 70 ? "bg-red-500" : riskPct > 30 ? "bg-yellow-400" : "bg-green-500"
                  }`}
                  style={{ width: `${riskPct}%` }}
                />
              </div>
            </>
          ) : (
            <p className="text-gray-500 text-sm">Waiting for data…</p>
          )}
        </div>
        <div className="rounded-xl bg-gray-800 p-5">
          <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">Findings</p>
          <p className="text-3xl font-bold">{status?.top_findings.length ?? 0}</p>
        </div>
      </div>

      {/* Findings */}
      <div className="rounded-xl bg-gray-800 p-5">
        <h2 className="text-lg font-semibold mb-4">Top Findings</h2>
        <FindingsPanel findings={status?.top_findings ?? []} />
      </div>

      {/* No data yet */}
      {!status && (
        <div className="mt-8 rounded-xl border border-dashed border-gray-700 p-8 text-center text-gray-500">
          No QC data yet. Start a session on the edge agent.
        </div>
      )}
    </div>
  );
}
