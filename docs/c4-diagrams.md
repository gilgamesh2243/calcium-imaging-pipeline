# C4 Architecture Diagrams

This document contains [C4 model](https://c4model.com) diagrams for the Calcium Imaging QC Pipeline at four levels of abstraction.

- [Level 1 – System Context](#level-1--system-context)
- [Level 2 – Container](#level-2--container)
- [Level 3 – Component (Core)](#level-3--component-core)
- [Level 3 – Component (Edge Agent)](#level-3--component-edge-agent)
- [Level 4 – Code (QC Algorithms)](#level-4--code-qc-algorithms)

---

## Level 1 – System Context

Shows the QC Pipeline as a single system and its relationships with users and external systems.

```mermaid
C4Context
  title System Context – Calcium Imaging QC Pipeline

  Person(scientist, "Scientist / Lab Operator", "Monitors live imaging sessions and acts on QC alerts.")

  System(pipeline, "Calcium Imaging QC Pipeline", "Streams microscopy frames in real time, detects acquisition failures, and surfaces alerts on a live dashboard.")

  System_Ext(acqSoftware, "Acquisition Software", "NIS-Elements, ScanImage, or custom system running on the acquisition PC. Produces raw fluorescence frames and experimental markers.")

  System_Ext(labLims, "Lab LIMS / Data Store", "Downstream lab information management or file-based storage where completed sessions are archived (optional integration).")

  Rel(scientist, pipeline, "Views live QC status, risk scores, and session history", "HTTPS / WebSocket")
  Rel(acqSoftware, pipeline, "Sends raw frames + experimental marker events", "gRPC stream (LZ4)")
  Rel(pipeline, labLims, "Exports session QC summary (optional)", "REST / file")
```

---

## Level 2 – Container

Shows the three runtime deployable units (containers) and the protocols between them.

```mermaid
C4Container
  title Container Diagram – Calcium Imaging QC Pipeline

  Person(scientist, "Scientist / Lab Operator")

  System_Ext(acqSoftware, "Acquisition Software", "NIS-Elements / custom")

  System_Boundary(pipeline, "Calcium Imaging QC Pipeline") {

    Container(edgeAgent, "Edge Agent", "C# .NET 8 / Windows Service", "Receives frames from acquisition software via an adapter, buffers them in a lock-free ring buffer, and streams batches to the core over gRPC.")

    Container(qcCore, "QC Core", "Python 3.11 / FastAPI / asyncio", "Ingests gRPC frame stream, runs QC algorithms, persists session data in SQLite, and exposes results via REST API and WebSocket.")

    ContainerDb(sessionDb, "Session Store", "SQLite (aiosqlite)", "Stores session manifests, per-frame QC findings, and risk-score history.")

    ContainerDb(auditLog, "Audit Trail", "JSONL flat file", "Append-only log of every inbound message for replay and debugging.")

    Container(dashboard, "Dashboard", "Next.js 14 / TypeScript / Tailwind CSS", "Single-page application showing live QC status, risk scores, per-finding details, and historical session list.")
  }

  Rel(acqSoftware, edgeAgent, "Raw frames + marker events", "In-process / named pipe / hotfolder (adapter-dependent)")
  Rel(edgeAgent, qcCore, "SessionManifest, FrameBatch, MarkerEvent", "gRPC stream (Protobuf + LZ4), TLS optional")
  Rel(qcCore, sessionDb, "Read / Write session & findings", "SQL (aiosqlite)")
  Rel(qcCore, auditLog, "Append raw messages", "File I/O (JSONL)")
  Rel(qcCore, dashboard, "QCStatus updates", "WebSocket (JSON)")
  Rel(dashboard, qcCore, "Session queries, health check", "REST HTTP /api/v1/...")
  Rel(scientist, dashboard, "Views live status and history", "HTTPS")
```

---

## Level 3 – Component (Core)

Shows the internal components of the **QC Core** container.

```mermaid
C4Component
  title Component Diagram – QC Core

  Container_Ext(edgeAgent, "Edge Agent", "C# .NET 8")
  Container_Ext(dashboard, "Dashboard", "Next.js 14")

  Container_Boundary(qcCore, "QC Core (Python)") {

    Component(ingestGw, "IngestGateway", "Python / grpcio", "gRPC server that accepts the SessionManifest, FrameBatch, and MarkerEvent streams from the edge agent.")

    Component(spooler, "Spooler", "Python / asyncio", "Writes every incoming message to the JSONL audit trail before forwarding to the QC engine.")

    Component(qcProcessor, "QCProcessor", "Python / NumPy", "Orchestrates the QC algorithm suite. Maintains per-session state, computes a composite risk score, and emits QCStatus after every N frames.")

    Component(baselineDrift, "BaselineDrift", "Python / NumPy", "Detects slow baseline drift using linear regression on mean fluorescence.")
    Component(saturation, "Saturation", "Python / NumPy", "Flags frames where more than X% of pixels exceed the sensor bit-depth ceiling.")
    Component(motion, "Motion", "Python / NumPy / SciPy", "Estimates inter-frame lateral drift using phase-correlation FFT.")
    Component(bleach, "Bleach", "Python / NumPy", "Fits an exponential decay to mean fluorescence to detect photobleaching.")
    Component(onsetLatency, "OnsetLatency", "Python", "Checks that the fluorescence response appears within the expected window after a DRUG_ON marker.")
    Component(focusProxy, "FocusProxy", "Python / NumPy", "Estimates focus quality via a high-frequency energy metric on each frame.")
    Component(markerMissing, "MarkerMissing", "Python", "Alerts when an expected experimental marker (e.g. DRUG_ON) is not received within the deadline.")

    Component(wsPublisher, "WSPublisher", "Python / FastAPI / WebSocket", "Maintains WebSocket connections to dashboard clients and broadcasts QCStatus JSON messages.")

    Component(restApi, "REST API", "Python / FastAPI", "Exposes /api/v1/health, /api/v1/sessions, and /api/v1/sessions/{id}/findings endpoints.")

    Component(sessionStore, "SessionStore", "Python / aiosqlite", "Async SQLite wrapper for session manifest and findings persistence.")
  }

  ContainerDb(db, "SQLite DB", "SQLite")
  ContainerDb(audit, "Audit JSONL", "Flat file")

  Rel(edgeAgent, ingestGw, "gRPC stream", "Protobuf + LZ4")
  Rel(ingestGw, spooler, "Raw messages")
  Rel(spooler, audit, "Append", "File I/O")
  Rel(ingestGw, qcProcessor, "Decoded frames & markers")
  Rel(qcProcessor, baselineDrift, "Frame batch")
  Rel(qcProcessor, saturation, "Frame batch")
  Rel(qcProcessor, motion, "Frame batch")
  Rel(qcProcessor, bleach, "Frame batch")
  Rel(qcProcessor, onsetLatency, "MarkerEvent + timing")
  Rel(qcProcessor, focusProxy, "Frame batch")
  Rel(qcProcessor, markerMissing, "Elapsed session time")
  Rel(qcProcessor, wsPublisher, "QCStatus")
  Rel(qcProcessor, sessionStore, "Persist findings")
  Rel(wsPublisher, dashboard, "QCStatus JSON", "WebSocket")
  Rel(restApi, sessionStore, "Query sessions / findings")
  Rel(restApi, dashboard, "Session data", "REST HTTP")
  Rel(sessionStore, db, "SQL")
```

---

## Level 3 – Component (Edge Agent)

Shows the internal components of the **Edge Agent** container.

```mermaid
C4Component
  title Component Diagram – Edge Agent (C# .NET 8)

  System_Ext(acqSoftware, "Acquisition Software", "NIS-Elements / custom")
  Container_Ext(qcCore, "QC Core", "Python / gRPC server")

  Container_Boundary(edgeAgent, "Edge Agent (C# .NET 8)") {

    Component(adapterHost, "AdapterHost", "C# / .NET 8", "Loads the configured IFrameSourceAdapter at startup, wires its events to the ring buffer, and manages the adapter lifecycle.")

    Component(adapter, "IFrameSourceAdapter", "C# interface / SDK", "Pluggable acquisition adapter. Bundled implementations: SimulatedAdapter, HotFolderAdapter, NisElementsAdapter.")

    Component(ringBuffer, "RingBuffer<Frame>", "C# / lock-free", "10-second circular buffer that decouples the acquisition thread from the gRPC streaming thread. Silently drops the oldest frame when full.")

    Component(streamerClient, "StreamerClient", "C# / Grpc.Net.Client", "Reads frame batches from the ring buffer, LZ4-compresses pixel data, and sends them to the core via a bidirectional gRPC stream.")

    Component(configLoader, "ConfigLoader", "C# / Microsoft.Extensions.Configuration", "Merges YAML config hierarchy with environment-variable overrides (QC_ prefix) at startup.")
  }

  Rel(acqSoftware, adapter, "Frames + markers", "In-process / hotfolder / API")
  Rel(adapter, adapterHost, "FrameReady, MarkerEmitted, SessionManifestReady events")
  Rel(adapterHost, ringBuffer, "Enqueue Frame")
  Rel(ringBuffer, streamerClient, "Dequeue batch")
  Rel(streamerClient, qcCore, "SessionManifest / FrameBatch / MarkerEvent", "gRPC stream (Protobuf + LZ4)")
  Rel(configLoader, adapterHost, "AdapterConfig")
  Rel(configLoader, streamerClient, "StreamingConfig")
```

---

## Level 4 – Code (QC Algorithms)

Shows the key classes and relationships within the **QCProcessor** and its algorithm modules.

```mermaid
classDiagram
  direction TB

  class QCProcessor {
    +session_manifest: SessionManifest
    +config: QCConfig
    +frame_count: int
    +risk_score: float
    +process_frame_batch(batch: FrameBatch) QCStatus
    +process_marker(event: MarkerEvent) None
    -_run_algorithms(frames) list~Finding~
    -_compute_risk_score(findings) float
  }

  class BaseAlgorithm {
    <<abstract>>
    +name: str
    +config: QCConfig
    +update(frames: ndarray, state: SessionState) Finding | None
    +reset() None
  }

  class BaselineDrift {
    -_mean_history: deque
    +update(frames, state) Finding | None
  }

  class Saturation {
    -_threshold_pct: float
    +update(frames, state) Finding | None
  }

  class Motion {
    -_reference_frame: ndarray
    -_cumulative_drift: float
    +update(frames, state) Finding | None
  }

  class Bleach {
    -_mean_history: deque
    +update(frames, state) Finding | None
  }

  class OnsetLatency {
    -_drug_on_time: float | None
    -_response_detected: bool
    +update(frames, state) Finding | None
    +on_marker(event: MarkerEvent) None
  }

  class FocusProxy {
    -_focus_history: deque
    +update(frames, state) Finding | None
  }

  class MarkerMissing {
    -_expected_markers: list~MarkerType~
    -_received_markers: set~MarkerType~
    +update(frames, state) Finding | None
    +on_marker(event: MarkerEvent) None
  }

  class Finding {
    +algorithm: str
    +severity: Severity
    +message: str
    +frame_index: int
    +metadata: dict
  }

  class QCStatus {
    +session_id: str
    +frame_index: int
    +risk_score: float
    +state: SessionState
    +findings: list~Finding~
    +timestamp_ns: int
  }

  QCProcessor --> BaseAlgorithm : runs suite of
  QCProcessor --> QCStatus : emits
  QCProcessor --> Finding : collects

  BaseAlgorithm <|-- BaselineDrift
  BaseAlgorithm <|-- Saturation
  BaseAlgorithm <|-- Motion
  BaseAlgorithm <|-- Bleach
  BaseAlgorithm <|-- OnsetLatency
  BaseAlgorithm <|-- FocusProxy
  BaseAlgorithm <|-- MarkerMissing

  BaseAlgorithm --> Finding : returns
```
