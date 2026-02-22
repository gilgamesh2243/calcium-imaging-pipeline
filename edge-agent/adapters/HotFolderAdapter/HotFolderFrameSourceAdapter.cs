using Microsoft.Extensions.Logging;
using QcAdapterSdk;

namespace HotFolderAdapter;

/// <summary>
/// Watches a folder for exported per-frame image files (*.raw or *.bin).
/// This is a fallback adapter for labs that export frames to disk rather than
/// streaming live (Mode B / hot-folder pattern).
/// </summary>
public sealed class HotFolderFrameSourceAdapter : IFrameSourceAdapter, IDisposable
{
    private readonly ILogger<HotFolderFrameSourceAdapter> _logger;
    private AdapterConfig? _config;
    private SessionPlan? _plan;
    private FileSystemWatcher? _watcher;
    private CancellationTokenSource? _cts;
    private ulong _frameIndex;

    public string Name => "HotFolderAdapter";
    public string Version => "0.1.0";
    public AdapterCapabilities Capabilities { get; } = new(
        SupportsLiveMode: false,
        SupportsReplay: true,
        SupportsHotFolder: true,
        SupportedModalities: ["2p-calcium", "widefield"]);

    public event EventHandler<FrameEventArgs>? FrameReady;
    public event EventHandler<MarkerEventArgs>? MarkerEmitted;
    public event EventHandler<SessionManifestEventArgs>? SessionManifestReady;

    public HotFolderFrameSourceAdapter(ILogger<HotFolderFrameSourceAdapter> logger)
    {
        _logger = logger;
    }

    public Task InitializeAsync(AdapterConfig config, CancellationToken ct = default)
    {
        _config = config;
        return Task.CompletedTask;
    }

    public Task StartSessionAsync(SessionPlan plan, CancellationToken ct = default)
    {
        _plan = plan;
        _cts = new CancellationTokenSource();

        var watchDir = plan.PlanMeta.GetValueOrDefault("hot_folder", "hot_folder");

        if (!Directory.Exists(watchDir))
            Directory.CreateDirectory(watchDir);

        _watcher = new FileSystemWatcher(watchDir)
        {
            Filter = "*.raw",
            NotifyFilter = NotifyFilters.FileName | NotifyFilters.CreationTime,
            EnableRaisingEvents = true,
        };
        _watcher.Created += OnFileCreated;

        var manifest = new SessionManifestEventArgs(
            SessionId: plan.SessionId,
            LabId: _config!.LabId,
            RigId: _config.RigId,
            Modality: _config.Modality,
            Fps: _config.Fps,
            Width: _config.Width,
            Height: _config.Height,
            Channels: [new ChannelInfo(0, "ch0", 0f, _config.BitDepth)],
            AcquisitionMeta: new Dictionary<string, string>(),
            PlanMeta: plan.PlanMeta,
            AdapterName: Name,
            AdapterVersion: Version);

        SessionManifestReady?.Invoke(this, manifest);
        _logger.LogInformation("HotFolderAdapter watching: {Dir}", watchDir);
        return Task.CompletedTask;
    }

    public Task StopSessionAsync(CancellationToken ct = default)
    {
        _cts?.Cancel();
        _watcher?.Dispose();
        _logger.LogInformation("HotFolderAdapter stopped.");
        return Task.CompletedTask;
    }

    private void OnFileCreated(object sender, FileSystemEventArgs e)
    {
        if (_plan is null || _config is null) return;
        try
        {
            var pixels = File.ReadAllBytes(e.FullPath);
            var ns = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1_000_000L;
            FrameReady?.Invoke(this, new FrameEventArgs(
                SessionId: _plan.SessionId,
                FrameIndex: _frameIndex++,
                TimestampMonoNs: ns,
                ChannelId: 0,
                Pixels: pixels,
                Width: _config.Width,
                Height: _config.Height,
                BitDepth: _config.BitDepth));
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to read frame file {Path}", e.FullPath);
        }
    }

    public void Dispose()
    {
        _watcher?.Dispose();
        _cts?.Dispose();
    }
}
