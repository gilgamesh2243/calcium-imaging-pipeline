# Configuration Reference

## Hierarchy

Config is loaded and deep-merged in order:
1. `configs/global.yaml` (base defaults)
2. `configs/labs/{lab_id}.yaml` (lab overrides)
3. `configs/rigs/{lab_id}/{rig_id}.yaml` (rig overrides)
4. Environment variables prefixed `QC_` (highest precedence)

## Config Sections

### `streaming`
| Key | Default | Description |
|-----|---------|-------------|
| `grpc_endpoint` | `localhost:50051` | Core gRPC address |
| `compression` | `lz4` | Frame compression (`lz4` or `none`) |
| `batch_size` | `8` | Frames per FrameBatch message |
| `ring_buffer_seconds` | `10` | Edge ring buffer depth in seconds |

### `qc`
| Key | Default | Description |
|-----|---------|-------------|
| `update_interval_frames` | `30` | Frames between QCStatus emissions |
| `saturation_threshold_pct` | `0.5` | % saturated pixels to trigger SATURATION |
| `baseline_drift_max_slope` | `0.005` | Normalised slope/frame for BASELINE_DRIFT |
| `baseline_std_max` | `0.05` | Normalised std for BASELINE_DRIFT |
| `max_drift_px` | `10.0` | Cumulative px drift for MOTION |
| `max_decay_constant` | `0.001` | Decay constant /frame for BLEACH |
| `expected_onset_min_s` | `5.0` | Earliest expected drug onset (s) |
| `expected_onset_max_s` | `60.0` | Latest expected drug onset (s) |
| `expected_markers` | `[DRUG_ON]` | Markers expected per session |
| `marker_deadline_seconds` | `300` | Deadline for expected markers |

### `security`
| Key | Default | Description |
|-----|---------|-------------|
| `auth_mode` | `token` | `token`, `mtls`, or `none` |
| `token` | `` | Auth token (set via env var) |
| `tls_cert` / `tls_key` | `` | Paths for mTLS |

## Environment Variable Overrides

Use `QC_SECTION__KEY=value` format:
```bash
QC_STREAMING__GRPC_ENDPOINT=192.168.1.100:50051
QC_QC__SATURATION_THRESHOLD_PCT=1.0
QC_SECURITY__TOKEN=mysecrettoken
```
