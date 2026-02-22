# Adapter Developer Guide

## Overview

The `qc-adapter-sdk` defines a stable `IFrameSourceAdapter` interface that any lab can implement to integrate their acquisition system with the QC pipeline.

## Interface

```csharp
public interface IFrameSourceAdapter
{
    string Name { get; }
    string Version { get; }
    AdapterCapabilities Capabilities { get; }

    Task InitializeAsync(AdapterConfig config, CancellationToken ct = default);
    Task StartSessionAsync(SessionPlan plan, CancellationToken ct = default);
    Task StopSessionAsync(CancellationToken ct = default);

    event EventHandler<FrameEventArgs>? FrameReady;
    event EventHandler<MarkerEventArgs>? MarkerEmitted;
    event EventHandler<SessionManifestEventArgs>? SessionManifestReady;
}
```

## Building a New Adapter

1. Create a new C# .NET 8 class library.
2. Add a reference to `QcAdapterSdk`.
3. Implement `IFrameSourceAdapter`.
4. Raise `FrameReady` for each acquired frame (from any thread – the `AdapterHost` is thread-safe).
5. Raise `MarkerEmitted` for experimental events (DRUG_ON, STIM_ON, etc.).
6. Raise `SessionManifestReady` at the beginning of each acquisition session.

## Key Rules

- **Never block the FrameReady event handler** – the pipeline is non-blocking.
- **Use monotonic timestamps** (`System.Diagnostics.Stopwatch`) for `TimestampMonoNs`.
- **Pixels must be little-endian uint16** (for UINT16 bit_depth).
- **Implement mock mode** that works without real hardware (see `NisElementsAdapter`).

## Configuration

Your adapter receives an `AdapterConfig` record containing:
- `LabId`, `RigId` – from the config hierarchy
- `Fps`, `Width`, `Height`, `BitDepth` – acquisition parameters
- `Extra` – dictionary for adapter-specific settings (e.g., `nis_host`, `camera_index`)

## Marker Mapping

Labs should define which acquisition event maps to which `MarkerType`:

```yaml
# configs/labs/my-lab.yaml
marker_mappings:
  drug_valve_open: DRUG_ON
  drug_valve_close: DRUG_OFF
  baseline_start: BASELINE_START
  baseline_end: BASELINE_END
```

## Lab Onboarding Checklist

- [ ] Define `lab_id` and `rig_id` naming conventions
- [ ] Map acquisition events to `MarkerType` values
- [ ] Define `expected_onset_min_s` / `expected_onset_max_s` per protocol
- [ ] Set `expected_baseline_seconds` per protocol
- [ ] Calibrate QC thresholds using 10 known-good sessions
- [ ] Choose adapter type (SimulatedAdapter / HotFolderAdapter / custom)
- [ ] Create `configs/labs/{lab_id}.yaml` and `configs/rigs/{lab_id}/{rig_id}.yaml`

## Reference Adapters

| Adapter | Use case |
|---------|----------|
| `SimulatedAdapter` | Demos, CI testing, no hardware needed |
| `HotFolderAdapter` | Labs exporting per-frame files to disk |
| `NisElementsAdapter` | Nikon NIS-Elements (scaffold; mock mode until Nikon API integrated) |
