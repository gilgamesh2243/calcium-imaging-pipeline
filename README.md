# Calcium Imaging QC Pipeline

A multi-lab deployable system that provides **real-time quality-control (QC) failure detection** during live two-photon / widefield calcium-imaging microscopy sessions.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Repository Layout](#repository-layout)
4. [Documentation](#documentation)
5. [Technology Stack](#technology-stack)
6. [Contributing](#contributing)

---

## Overview

The pipeline continuously monitors frames from an acquisition PC, streams them over gRPC to a GPU processing node, runs a suite of QC algorithms, and pushes live status to a Next.js dashboard.

Key capabilities:

| Capability | Detail |
|---|---|
| **Real-time QC** | Baseline drift, saturation, motion, photobleach, focus proxy, onset latency, missing marker detection |
| **Non-blocking acquisition** | Lock-free ring buffer; frames are never blocked by the QC path |
| **Multi-lab support** | YAML config hierarchy (global → lab → rig) with env-var overrides |
| **Pluggable adapters** | Stable `IFrameSourceAdapter` SDK for any acquisition system |
| **Resilient streaming** | Edge agent continues recording locally if the core is unreachable |

---

## Quick Start

### Prerequisites

- Docker Engine 24+ with Compose plugin
- (Optional) NVIDIA GPU on the core node for accelerated QC

### 1 – Start core services

```bash
cd core/docker
docker compose up -d
```

- **gRPC ingest**: `localhost:50051`
- **REST / WebSocket API**: `localhost:8000`
- **Dashboard**: `http://localhost:3000`

### 2 – Verify health

```bash
curl http://localhost:8000/api/v1/health
# → {"status": "ok"}
```

### 3 – Stream a test replay

```bash
cd replay-testkit
pip install -e .
python -m replay_server.server --endpoint localhost:50051 --fps 30 --frames 300
```

Open `http://localhost:3000/live` to watch the live dashboard.

### 4 – Deploy the edge agent (Windows acquisition PC)

```bash
cd edge-agent
dotnet publish -c Release -r win-x64 --self-contained
# Copy output to acquisition PC, then set env vars:
#   QC_CORE_ENDPOINT=http://<core-ip>:50051
#   QC_LAB_ID=my-lab
#   QC_RIG_ID=rig-a
#   QC_ADAPTER=simulated
QcEdgeAgent.exe
```

---

## Repository Layout

```
calcium-imaging-pipeline/
├── configs/                  # YAML config hierarchy (global → lab → rig)
├── core/                     # Python QC core (FastAPI + gRPC server)
│   ├── qc_core/
│   │   ├── algorithms/       # QC algorithm modules
│   │   ├── api/              # FastAPI REST routes
│   │   ├── ingest_gateway/   # gRPC server + audit spooler
│   │   ├── qc_engine/        # QCProcessor orchestrator
│   │   ├── storage/          # SQLite session store
│   │   └── websocket/        # WebSocket publisher
│   └── docker/               # Docker Compose files
├── dashboard/                # Next.js 14 dashboard (TypeScript, Tailwind)
├── docs/                     # Documentation
│   ├── architecture.md       # System architecture overview
│   ├── c4-diagrams.md        # C4 model diagrams (system → code level)
│   ├── adapter_dev_guide.md  # Guide for building custom adapters
│   ├── configs.md            # Configuration reference
│   ├── deployment.md         # Deployment guide
│   └── troubleshooting.md    # Troubleshooting guide
├── edge-agent/               # C# .NET 8 edge agent + adapter SDK
│   ├── src/QcEdgeAgent/      # Main edge agent host
│   └── src/QcAdapterSdk/     # Stable adapter interface & base classes
├── proto/                    # Protobuf definitions (qcstream.proto)
└── replay-testkit/           # Python replay server for integration testing
```

---

## Documentation

| Document | Description |
|---|---|
| [Architecture Overview](docs/architecture.md) | High-level data-flow and safety guarantees |
| [C4 Diagrams](docs/c4-diagrams.md) | C4 model – System Context, Container, Component, and Code diagrams |
| [Deployment Guide](docs/deployment.md) | Docker Compose, edge agent setup, TLS/auth |
| [Configuration Reference](docs/configs.md) | Full config key reference and env-var overrides |
| [Adapter Developer Guide](docs/adapter_dev_guide.md) | SDK interface, rules, lab onboarding checklist |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |

---

## Technology Stack

| Component | Technology |
|---|---|
| Edge agent | C# .NET 8 |
| Core ingest + QC | Python 3.11, FastAPI, asyncio |
| Transport | gRPC (Protobuf), LZ4 compression |
| Dashboard | Next.js 14, TypeScript, Tailwind CSS |
| Storage | SQLite (aiosqlite), JSONL audit trail |
| Container | Docker Compose |

---

## Contributing

1. Fork the repo and create a feature branch.
2. For new acquisition adapters follow the [Adapter Developer Guide](docs/adapter_dev_guide.md).
3. Add or update tests under `core/tests/`, `edge-agent/tests/`, or `replay-testkit/`.
4. Open a pull request describing your change.