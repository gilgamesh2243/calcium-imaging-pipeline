"""
gRPC ingest server.

Starts a gRPC server that accepts:
  - SendSessionManifest (unary)
  - SendFrameBatches    (client streaming)
  - SendMarkerEvent     (unary)
  - StreamFramesAndMarkers (bidirectional streaming)
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import grpc
from grpc import aio as grpc_aio

from qc_core.proto_gen import ensure_generated

logger = logging.getLogger(__name__)


async def serve(
    processor: Any,
    spooler: Any,
    store: Any,
    ws_publisher: Any,
    host: str = "0.0.0.0",
    port: int = 50051,
) -> grpc_aio.Server:
    ensure_generated()

    # Import after generation
    from qc_core.generated import qcstream_pb2, qcstream_pb2_grpc  # type: ignore

    class QcIngestServicer(qcstream_pb2_grpc.QcIngestServiceServicer):
        async def SendSessionManifest(self, request, context):
            manifest = _manifest_to_dict(request)
            logger.info("Session manifest received: %s", manifest.get("session_id"))
            processor.init_session(manifest)
            spooler.write_manifest(manifest["session_id"], manifest)
            await store.upsert_session(manifest)
            return qcstream_pb2.IngestResponse(accepted=True, message="ok")

        async def SendFrameBatches(self, request_iterator, context):
            count = 0
            async for batch in request_iterator:
                d = _batch_to_dict(batch)
                qc = await processor.process_frame_batch(d)
                if qc:
                    spooler.append_qc_status(d["session_id"], qc)
                    await store.insert_qc_status(
                        d["session_id"],
                        qc["t_eval_mono_ns"],
                        qc["state"],
                        qc["risk_score"],
                        qc["top_findings"],
                    )
                    await ws_publisher.broadcast(qc)
                count += 1
            return qcstream_pb2.IngestResponse(accepted=True, message=f"processed {count} batches")

        async def SendMarkerEvent(self, request, context):
            event = _marker_to_dict(request)
            session_id = event["session_id"]
            await processor.process_marker(event)
            spooler.append_marker(session_id, event)
            await store.insert_marker(
                session_id,
                event["t_mono_ns"],
                str(event["type"]),
                event.get("value", ""),
            )
            return qcstream_pb2.IngestResponse(accepted=True, message="ok")

        async def StreamFramesAndMarkers(self, request_iterator, context):
            async for batch in request_iterator:
                d = _batch_to_dict(batch)
                qc = await processor.process_frame_batch(d)
                if qc:
                    spooler.append_qc_status(d["session_id"], qc)
                    await store.insert_qc_status(
                        d["session_id"],
                        qc["t_eval_mono_ns"],
                        qc["state"],
                        qc["risk_score"],
                        qc["top_findings"],
                    )
                    await ws_publisher.broadcast(qc)
                    yield _qc_to_proto(qc, qcstream_pb2)

    server = grpc_aio.server()
    qcstream_pb2_grpc.add_QcIngestServiceServicer_to_server(QcIngestServicer(), server)
    listen_addr = f"{host}:{port}"
    server.add_insecure_port(listen_addr)
    await server.start()
    logger.info("gRPC ingest server listening on %s", listen_addr)
    return server


# ─── conversion helpers ──────────────────────────────────────────────────────

def _manifest_to_dict(req: Any) -> dict[str, Any]:
    return {
        "session_id": req.session_id,
        "lab_id": req.lab_id,
        "rig_id": req.rig_id,
        "modality": req.modality,
        "width": req.width,
        "height": req.height,
        "fps": req.fps,
        "channels": [
            {
                "channel_id": c.channel_id,
                "name": c.name,
                "wavelength": c.wavelength,
                "bit_depth": c.bit_depth,
            }
            for c in req.channels
        ],
        "acquisition_meta": dict(req.acquisition_meta),
        "plan_meta": dict(req.plan_meta),
        "edge_agent_version": req.edge_agent_version,
        "adapter_name": req.adapter_name,
        "adapter_version": req.adapter_version,
        "manifest_sha256": req.manifest_sha256,
    }


def _batch_to_dict(req: Any) -> dict[str, Any]:
    return {
        "session_id": req.session_id,
        "batch_index": req.batch_index,
        "first_frame_index": req.first_frame_index,
        "frame_count": req.frame_count,
        "t0_mono_ns": req.t0_mono_ns,
        "dt_ns": req.dt_ns,
        "channel_id": req.channel_id,
        "payload": bytes(req.payload),
        "pixel_format": req.pixel_format,
        "width": req.width,
        "height": req.height,
        "batch_meta": dict(req.batch_meta),
    }


def _marker_to_dict(req: Any) -> dict[str, Any]:
    return {
        "session_id": req.session_id,
        "t_mono_ns": req.t_mono_ns,
        "type": req.type,
        "value": req.value,
        "meta": dict(req.meta),
    }


def _qc_to_proto(qc: dict[str, Any], pb2: Any) -> Any:
    state_map = {"GREEN": 1, "YELLOW": 2, "RED": 3}
    finding_type_map = {
        "FLOW_DELAY": 1, "BASELINE_DRIFT": 2, "MOTION": 3,
        "BLEACH": 4, "SATURATION": 5, "FOCUS_DRIFT": 6, "MARKER_MISSING": 7,
    }
    findings = []
    for f in qc.get("top_findings", []):
        ev = f.get("evidence", {})
        findings.append(
            pb2.Finding(
                type=finding_type_map.get(f.get("type", ""), 0),
                confidence=f.get("confidence", 0.0),
                summary=f.get("summary", ""),
                evidence=pb2.EvidenceRef(
                    frame_start=ev.get("frame_start", 0),
                    frame_end=ev.get("frame_end", 0),
                    metric_trace_ids=ev.get("metric_trace_ids", []),
                ),
            )
        )
    return pb2.QCStatus(
        session_id=qc["session_id"],
        t_eval_mono_ns=qc["t_eval_mono_ns"],
        state=state_map.get(qc.get("state", "GREEN"), 1),
        risk_score=qc.get("risk_score", 0.0),
        top_findings=findings,
    )
