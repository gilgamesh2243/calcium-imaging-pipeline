# Deployment Guide

## Quick Start (Docker Compose)

### Prerequisites
- Docker Engine 24+ with Compose plugin
- GPU node (optional for GPU-accelerated QC)

### 1. Start Core + Dashboard

```bash
cd core/docker
docker compose up -d
```

Services started:
- `qc-core` on ports `50051` (gRPC) and `8000` (HTTP/WS)
- `qc-dashboard` on port `3000`

### 2. Verify health

```bash
curl http://localhost:8000/api/v1/health
# → {"status": "ok"}
```

Open `http://localhost:3000` in a browser.

### 3. Install Edge Agent (Windows)

1. Build the edge agent:
   ```
   cd edge-agent
   dotnet publish -c Release -r win-x64 --self-contained
   ```
2. Copy the output to the acquisition PC.
3. Set environment variables:
   ```
   QC_CORE_ENDPOINT=http://<core-ip>:50051
   QC_LAB_ID=my-lab
   QC_RIG_ID=rig-a
   QC_ADAPTER=simulated   # or hotfolder
   ```
4. Run `QcEdgeAgent.exe`.

### 4. Stream a test replay

```bash
cd replay-testkit
pip install -e .
python -m replay_server.server --endpoint localhost:50051 --fps 30 --frames 300
```

Watch the dashboard at `http://localhost:3000/live`.

## Configuration

See `configs/` for the YAML configuration hierarchy:
- `global.yaml` – defaults
- `labs/{lab_id}.yaml` – lab overrides
- `rigs/{lab_id}/{rig_id}.yaml` – rig overrides

Environment variable overrides: prefix with `QC_` and use `__` as separator.
Example: `QC_STREAMING__GRPC_ENDPOINT=192.168.1.50:50051`

## TLS / Auth (optional)

Set in `configs/global.yaml` or via environment:
```bash
QC_SECURITY__AUTH_MODE=token
QC_SECURITY__TOKEN=your-secret-token
```

For mTLS:
```bash
QC_SECURITY__AUTH_MODE=mtls
QC_SECURITY__TLS_CERT=/path/to/cert.pem
QC_SECURITY__TLS_KEY=/path/to/key.pem
```
