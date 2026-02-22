using Microsoft.Extensions.Logging;
using QcAdapterSdk;

namespace NisElementsAdapter;

/// <summary>
/// Scaffold for the NIS-Elements (Nikon) adapter.
///
/// This adapter compiles and runs in "mock mode" using the SimulatedAdapter
/// internals until the real Nikon API/Add-in integration is available.
///
/// Integration points (TODO – requires Nikon SDK):
///   - Hook into NIS-Elements COM/IPC events for OnFrame
///   - Subscribe to macro/script events for markers (DRUG_ON etc.)
///   - Read session metadata from NIS ND2 acquisition plan
///
/// See docs/adapter_dev_guide.md for details.
/// </summary>
public sealed class NisElementsFrameSourceAdapter : IFrameSourceAdapter, IDisposable
{
    private readonly ILogger<NisElementsFrameSourceAdapter> _logger;
    private readonly bool _mockMode;
    private IFrameSourceAdapter? _mockAdapter;

    public string Name => "NisElementsAdapter";
    public string Version => "0.1.0-scaffold";
    public AdapterCapabilities Capabilities { get; } = new(
        SupportsLiveMode: true,
        SupportsReplay: false,
        SupportsHotFolder: false,
        SupportedModalities: ["2p-calcium", "widefield"]);

    public event EventHandler<FrameEventArgs>? FrameReady;
    public event EventHandler<MarkerEventArgs>? MarkerEmitted;
    public event EventHandler<SessionManifestEventArgs>? SessionManifestReady;

    public NisElementsFrameSourceAdapter(
        ILogger<NisElementsFrameSourceAdapter> logger,
        bool mockMode = true)
    {
        _logger = logger;
        _mockMode = mockMode;
    }

    public async Task InitializeAsync(AdapterConfig config, CancellationToken ct = default)
    {
        if (_mockMode)
        {
            _logger.LogWarning("NisElementsAdapter running in MOCK MODE – using SimulatedAdapter.");
            var mockLogger = Microsoft.Extensions.Logging.Abstractions.NullLoggerFactory.Instance
                .CreateLogger<SimulatedAdapter.SimulatedFrameSourceAdapter>();
            _mockAdapter = new SimulatedAdapter.SimulatedFrameSourceAdapter(mockLogger);
            _mockAdapter.FrameReady += (s, e) => FrameReady?.Invoke(s, e);
            _mockAdapter.MarkerEmitted += (s, e) => MarkerEmitted?.Invoke(s, e);
            _mockAdapter.SessionManifestReady += (s, e) => SessionManifestReady?.Invoke(s, e);
            await _mockAdapter.InitializeAsync(config, ct);
        }
        else
        {
            // TODO: Initialise Nikon NIS-Elements API
            // Example (requires Nikon SDK DLL):
            //   NisApi.Initialize(config.Extra["nis_host"]);
            throw new NotImplementedException(
                "Real NIS-Elements integration not yet implemented. Set mockMode=true.");
        }
    }

    public Task StartSessionAsync(SessionPlan plan, CancellationToken ct = default)
    {
        if (_mockAdapter is not null)
            return _mockAdapter.StartSessionAsync(plan, ct);

        // TODO: Start NIS-Elements acquisition
        throw new NotImplementedException("NIS-Elements integration pending.");
    }

    public Task StopSessionAsync(CancellationToken ct = default)
    {
        if (_mockAdapter is not null)
            return _mockAdapter.StopSessionAsync(ct);

        // TODO: Stop NIS-Elements acquisition
        return Task.CompletedTask;
    }

    public void Dispose()
    {
        if (_mockAdapter is IDisposable d)
            d.Dispose();
    }
}
