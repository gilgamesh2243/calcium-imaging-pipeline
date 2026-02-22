# System Architecture

> For structured C4 model diagrams (System Context, Container, Component, and Code level) see **[C4 Diagrams](c4-diagrams.md)**.

## Overview

The calcium imaging QC pipeline is a multi-lab deployable system providing real-time failure detection during live microscopy sessions.

```
┌─────────────────────────────────────────────────────────────────┐
│  Acquisition PC (Edge)                                          │
│                                                                 │
│  ┌─────────────────┐   frames    ┌──────────────┐              │
│  │ NIS-Elements /  │ ──────────► │  AdapterHost │              │
│  │ Other acq. sw.  │   markers   │              │              │
│  └─────────────────┘             └──────┬───────┘              │
│                                         │                       │
│                              ┌──────────▼──────────┐           │
│                              │   RingBuffer<Frame>  │           │
│                              │   (10s, lock-free)   │           │
│                              └──────────┬───────────┘           │
│                                         │                       │
│                              ┌──────────▼──────────┐           │
│                              │   StreamerClient     │           │
│                              │   (gRPC, LZ4)        │           │
│                              └──────────┬───────────┘           │
└─────────────────────────────────────────┼───────────────────────┘
                                          │ gRPC stream
┌─────────────────────────────────────────▼───────────────────────┐
│  GPU Processing Node (Core)                                      │
│                                                                  │
│  ┌──────────────────┐    ┌─────────────────────┐               │
│  │  IngestGateway   │───►│    QCProcessor       │               │
│  │  (gRPC server)   │    │                      │               │
│  └──────────────────┘    │  • BaselineDrift      │               │
│                           │  • Saturation         │               │
│  ┌──────────────────┐    │  • Motion             │               │
│  │   Spooler        │    │  • Bleach             │               │
│  │   (audit trail)  │    │  • OnsetLatency       │               │
│  └──────────────────┘    │  • FocusProxy         │               │
│                           │  • MarkerMissing      │               │
│  ┌──────────────────┐    └──────────┬────────────┘               │
│  │   SessionStore   │               │ QCStatus                   │
│  │   (SQLite)       │               │                            │
│  └──────────────────┘    ┌──────────▼────────────┐               │
│                           │   WSPublisher         │               │
│                           │   (WebSocket)         │               │
│  ┌──────────────────┐    └──────────┬────────────┘               │
│  │   FastAPI REST   │               │                            │
│  │   /api/v1/...    │               │                            │
│  └──────────────────┘               │                            │
└────────────────────────────────────┼─────────────────────────────┘
                                     │ WebSocket / REST
┌────────────────────────────────────▼─────────────────────────────┐
│  Dashboard (Next.js)                                              │
│  • Live session view (state, risk score, findings)                │
│  • Sessions list                                                  │
└────────────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **SessionManifest** – sent once at session start, contains lab/rig metadata, channel config, plan parameters.
2. **FrameBatch** – streamed continuously; LZ4-compressed uint16 pixel data + timing.
3. **MarkerEvent** – asynchronous; marks experimental events (DRUG_ON, BASELINE_START, etc.).
4. **QCStatus** – pushed to dashboard via WebSocket after every N frames; contains state, risk score, top findings.

## Safety Guarantees

- Acquisition **never blocks**: frames are enqueued into a ring buffer; if full, the oldest frame is silently dropped.
- If the core is unreachable, the edge agent logs `StreamFailed` and continues recording locally.
- Backpressure tiers: (1) drop preview → (2) decimate QC stream → (3) pause pixels, keep markers.

## Technology Stack

| Component | Technology |
|-----------|------------|
| Edge agent | C# .NET 8 |
| Core ingest + QC | Python 3.11, FastAPI, asyncio |
| Transport | gRPC (Protobuf), LZ4 compression |
| Dashboard | Next.js 14, TypeScript, Tailwind |
| Storage | SQLite (aiosqlite), JSONL audit trail |
| Container | Docker Compose |
