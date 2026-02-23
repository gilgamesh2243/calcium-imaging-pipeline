# Real-Time Experimental QC Platform

**Multi-Lab Streaming Failure Detection for Preclinical Imaging**

------------------------------------------------------------------------

## Overview

This project provides a **real-time quality control (QC) and failure
detection pipeline** for microscopy / calcium imaging experiments.

It is designed to:

-   Detect acquisition failures **during or immediately after
    recording**
-   Reduce experimental variance by catching issues early
-   Improve reproducibility across operators and rigs
-   Decrease reruns, wasted sessions, and unnecessary animal usage
-   Provide NIH-grade auditability through deterministic QC and golden
    tests

The system supports **multi-lab deployment** using configuration
hierarchies and adapter-based acquisition integrations.

------------------------------------------------------------------------

## Why This Exists

In many imaging workflows:

-   A session fails due to flow issues, motion, bleaching, saturation,
    or mistimed stimulus.
-   The problem is only discovered **after multiple recordings are
    complete**.
-   Variability between operators increases required sample sizes (the
    "variance tax").
-   Power analyses inflate N due to acquisition variability rather than
    biology.

This platform addresses that by:

1.  Streaming acquisition data in real time.
2.  Running deterministic QC detectors.
3.  Flagging issues before the next experiment begins.
4.  Logging every decision for reproducibility.

The goal is not automation for its own sake --- it is **variance
suppression and early failure detection**.

------------------------------------------------------------------------

## What It Does (Current Capabilities)

### Deterministic QC Detectors (v1)

-   Baseline drift detection\
-   Baseline variance instability\
-   Saturation / clipping detection\
-   Motion / drift detection (frame-to-frame correlation shift)\
-   Photobleach slope estimation\
-   Focus proxy (Laplacian / Tenengrad trend)\
-   Onset latency detection relative to `DRUG_ON` markers\
-   Missing expected markers

All detectors are deterministic in v1.\
Given identical input frames + configuration → identical QC result.

------------------------------------------------------------------------

## Architecture

``` mermaid
flowchart LR
    A[Acquisition PC
Edge Agent + Adapter] -->|gRPC FrameBatch + MarkerEvent| B[QC Core Ingest]
    B --> C[QC Engine]
    C --> D[WebSocket Status Publisher]
    D --> E[Dashboard UI]
    B --> F[Session Spool + Audit Storage]
    G[Replay Testkit] --> B
```

------------------------------------------------------------------------

## Mode A vs Mode B

### Mode A --- True Frame Streaming (Preferred)

-   Direct frame tap from acquisition software (via adapter)
-   Lowest latency
-   Requires SDK or integration layer

### Mode B --- ND2 Tail / Near-Real-Time

-   Watches growing ND2 file
-   Easier integration
-   Slightly higher latency

Current repo state: - Core, dashboard, replay, QC engine implemented -
Adapter integration scaffolded - Nikon NIS-Elements adapter pending
integration

------------------------------------------------------------------------

## Quickstart (Local Development)

### 1. Start Core + Dashboard

``` bash
cd core/docker
docker compose up --build
```

Services:

-   gRPC ingest: `localhost:50051`
-   HTTP API + WebSocket: `http://localhost:8000`
-   Dashboard: `http://localhost:3000`

------------------------------------------------------------------------

### 2. Confirm Health

``` bash
curl http://localhost:8000/api/v1/health
```

------------------------------------------------------------------------

### 3. Run Tests

``` bash
cd core
pytest
```

------------------------------------------------------------------------

### 4. Run Golden Tests

``` bash
python replay-testkit/golden_tests/runner.py
```

------------------------------------------------------------------------

## Multi-Lab Configuration Model

Configuration hierarchy:

    configs/
      global.yaml
      labs/{lab_id}.yaml
      rigs/{lab_id}/{rig_id}.yaml

Override order:

    global → lab → rig

------------------------------------------------------------------------

## Validation & Reproducibility

Each session stores:

-   manifest.json
-   markers.jsonl
-   qc_status.jsonl
-   metrics.parquet
-   Evidence snippets
-   Version metadata

Golden tests enforce deterministic QC behavior and NIH-grade audit
traceability.

------------------------------------------------------------------------

## Repository Layout

    /core
    /dashboard
    /replay-testkit
    /configs
    /proto

------------------------------------------------------------------------

## Current Status

  Feature                             Status
  ----------------------------------- -------------
  gRPC ingest                         Implemented
  Deterministic QC engine             Implemented
  Dashboard live status               Implemented
  Replay simulation                   Implemented
  Golden tests                        Implemented
  Multi-lab config hierarchy          Implemented
  Edge agent (Windows)                In progress
  Nikon adapter integration           Planned
  ROI-based QC                        Planned
  ML-based early failure prediction   Planned

------------------------------------------------------------------------

## Intended Use

This platform is a research tool designed to:

-   Improve experimental reliability
-   Reduce acquisition-related variance
-   Support reproducible preclinical research

It is not a medical device.
