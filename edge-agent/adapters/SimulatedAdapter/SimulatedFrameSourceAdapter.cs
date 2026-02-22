using System.Security.Cryptography;
using Microsoft.Extensions.Logging;
using QcAdapterSdk;

namespace SimulatedAdapter;

/// <summary>
/// Generates synthetic uint16 frames at the configured fps.
/// Used for integration testing and demos without a microscope.
/// </summary>
public sealed class SimulatedFrameSourceAdapter : IFrameSourceAdapter, IDisposable
{
    private readonly ILogger<SimulatedFrameSourceAdapter> _logger;
    private AdapterConfig? _config;
    private SessionPlan? _plan;
    private CancellationTokenSource? _cts;
    private Task? _produceTask;

    public string Name => "SimulatedAdapter";
    public string Version => "0.1.0";
    public AdapterCapabilities Capabilities { get; } = new(
        SupportsLiveMode: true,
        SupportsReplay: true,
        SupportsHotFolder: false,
        SupportedModalities: ["2p-calcium", "widefield"]);

    public event EventHandler<FrameEventArgs>? FrameReady;
    public event EventHandler<MarkerEventArgs>? MarkerEmitted;
    public event EventHandler<SessionManifestEventArgs>? SessionManifestReady;

    public SimulatedFrameSourceAdapter(ILogger<SimulatedFrameSourceAdapter> logger)
    {
        _logger = logger;
    }

    public Task InitializeAsync(AdapterConfig config, CancellationToken ct = default)
    {
        _config = config;
        _logger.LogInformation("SimulatedAdapter initialized for {Lab}/{Rig}", config.LabId, config.RigId);
        return Task.CompletedTask;
    }

    public Task StartSessionAsync(SessionPlan plan, CancellationToken ct = default)
    {
        _plan = plan;
        _cts = new CancellationTokenSource();

        var manifest = new SessionManifestEventArgs(
            SessionId: plan.SessionId,
            LabId: _config!.LabId,
            RigId: _config.RigId,
            Modality: _config.Modality,
            Fps: _config.Fps,
            Width: _config.Width,
            Height: _config.Height,
            Channels: [new ChannelInfo(0, "GCaMP", 488f, _config.BitDepth)],
            AcquisitionMeta: new Dictionary<string, string> { ["objective"] = "16x" },
            PlanMeta: plan.PlanMeta,
            AdapterName: Name,
            AdapterVersion: Version);

        SessionManifestReady?.Invoke(this, manifest);

        _produceTask = Task.Run(() => ProduceFramesAsync(_cts.Token), ct);
        _logger.LogInformation("SimulatedAdapter session started: {SessionId}", plan.SessionId);
        return Task.CompletedTask;
    }

    public async Task StopSessionAsync(CancellationToken ct = default)
    {
        _cts?.Cancel();
        if (_produceTask is not null)
        {
            try { await _produceTask.WaitAsync(TimeSpan.FromSeconds(5), ct); }
            catch { /* expected on cancel */ }
        }
        _logger.LogInformation("SimulatedAdapter session stopped.");
    }

    private async Task ProduceFramesAsync(CancellationToken ct)
    {
        if (_config is null || _plan is null) return;

        var fps = _config.Fps;
        var w = _config.Width;
        var h = _config.Height;
        var delayMs = (int)(1000.0 / fps);
        ulong frameIndex = 0;
        var t0 = System.Diagnostics.Stopwatch.GetTimestamp();
        var ticksPerNs = System.Diagnostics.Stopwatch.Frequency / 1_000_000_000.0;
        var rng = RandomNumberGenerator.Create();

        // Emit a BASELINE_START marker at the beginning
        EmitMarker("BASELINE_START", "", ct);

        // Emit DRUG_ON after baseline period
        var baselineFrames = (int)(_plan.ExpectedBaselineSeconds * fps);
        var drugOnEmitted = false;

        while (!ct.IsCancellationRequested)
        {
            var pixels = new byte[w * h * 2]; // uint16 → 2 bytes/pixel
            rng.GetBytes(pixels);
            NormalizePixels(pixels);

            var ticks = System.Diagnostics.Stopwatch.GetTimestamp() - t0;
            var monoNs = (long)(ticks / ticksPerNs);

            FrameReady?.Invoke(this, new FrameEventArgs(
                SessionId: _plan.SessionId,
                FrameIndex: frameIndex,
                TimestampMonoNs: monoNs,
                ChannelId: 0,
                Pixels: pixels,
                Width: w,
                Height: h,
                BitDepth: _config.BitDepth));

            if (!drugOnEmitted && frameIndex >= (ulong)baselineFrames)
            {
                EmitMarker("DRUG_ON", "drug_a", ct);
                drugOnEmitted = true;
            }

            frameIndex++;
            try { await Task.Delay(delayMs, ct); }
            catch (OperationCanceledException) { break; }
        }
    }

    private static void NormalizePixels(byte[] pixels)
    {
        // Normalise to a sensible range (0x4000–0x5000)
        var span = System.Runtime.InteropServices.MemoryMarshal.Cast<byte, ushort>(pixels);
        for (int i = 0; i < span.Length; i++)
            span[i] = (ushort)((span[i] % 0x1000) + 0x4000);
    }

    private void EmitMarker(string markerType, string value, CancellationToken _)
    {
        var ticks = System.Diagnostics.Stopwatch.GetTimestamp();
        var ns = (long)(ticks / (System.Diagnostics.Stopwatch.Frequency / 1_000_000_000.0));
        MarkerEmitted?.Invoke(this, new MarkerEventArgs(
            SessionId: _plan!.SessionId,
            TimestampMonoNs: ns,
            MarkerType: markerType,
            Value: value,
            Meta: new Dictionary<string, string>()));
    }

    public void Dispose()
    {
        _cts?.Cancel();
        _cts?.Dispose();
    }
}
