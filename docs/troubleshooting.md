# Troubleshooting Guide

## Edge Agent

### "StreamFailed" in logs
**Cause**: Core is unreachable or returned an error.  
**Fix**: Check `QC_CORE_ENDPOINT` is correct and core is running. Recording continues normally.

### No frames in dashboard
**Check**:
1. Is `QcEdgeAgent` running? Look for "Session started" in logs.
2. Is the adapter producing frames? Try `QC_ADAPTER=simulated`.
3. Is the gRPC endpoint reachable from the edge PC?

### High drop count
**Cause**: Ring buffer overflowing (core too slow or network congestion).  
**Fix**: Increase `QC_BUFFER_SECONDS`, reduce `QC_FPS`, or use frame decimation.

---

## Core (qc-core)

### gRPC server fails to start
**Cause**: Port 50051 in use.  
**Fix**: Set `QC_GRPC_PORT=50052`.

### `protoc` errors at startup
**Cause**: `grpcio-tools` not installed or `proto/qcstream.proto` not found.  
**Fix**: `pip install grpcio-tools` and ensure `proto/` is accessible.

### High CPU on QCProcessor
**Cause**: Motion detector (phase correlation FFT) is expensive.  
**Fix**: Reduce frame size, increase `update_interval_frames`, or disable motion detector.

---

## Dashboard

### "Disconnected" shown
**Cause**: WebSocket to `qc-core:8000/ws/qc` not reachable.  
**Fix**: Check `NEXT_PUBLIC_WS_URL` env var and network connectivity.

### Sessions page shows "Could not load sessions"
**Cause**: REST API unreachable.  
**Fix**: Check `NEXT_PUBLIC_API_URL` and ensure `qc-core` is healthy.

---

## Replay Testkit

### `protoc` error in replay_server
**Cause**: `grpcio-tools` not installed.  
**Fix**: `pip install grpcio-tools`.

### Golden test hash mismatch
**Cause**: Algorithm code changed.  
**Action**: If the change is intentional, regenerate golden files with `run_golden()` and update stored hashes.
