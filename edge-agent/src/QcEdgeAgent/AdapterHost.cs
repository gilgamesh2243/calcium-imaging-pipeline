using Microsoft.Extensions.Logging;
using QcAdapterSdk;

namespace QcEdgeAgent;

/// <summary>
/// Hosts an IFrameSourceAdapter and feeds frames into the RingBuffer.
/// Decouples adapter events from the streamer so acquisition never blocks.
/// </summary>
public sealed class AdapterHost : IDisposable
{
    private readonly IFrameSourceAdapter _adapter;
    private readonly RingBuffer<FrameEventArgs> _buffer;
    private readonly ILogger<AdapterHost> _logger;
    private bool _disposed;

    public AdapterHost(
        IFrameSourceAdapter adapter,
        RingBuffer<FrameEventArgs> buffer,
        ILogger<AdapterHost> logger)
    {
        _adapter = adapter;
        _buffer = buffer;
        _logger = logger;

        _adapter.FrameReady += OnFrameReady;
        _adapter.MarkerEmitted += OnMarkerEmitted;
        _adapter.SessionManifestReady += OnSessionManifestReady;
    }

    public event EventHandler<MarkerEventArgs>? MarkerEmitted;
    public event EventHandler<SessionManifestEventArgs>? SessionManifestReady;

    private void OnFrameReady(object? sender, FrameEventArgs e)
    {
        // NEVER block acquisition – just enqueue (drop oldest if full)
        _buffer.Enqueue(e);
    }

    private void OnMarkerEmitted(object? sender, MarkerEventArgs e)
    {
        _logger.LogInformation("Marker: {Type} @ {T}", e.MarkerType, e.TimestampMonoNs);
        MarkerEmitted?.Invoke(this, e);
    }

    private void OnSessionManifestReady(object? sender, SessionManifestEventArgs e)
    {
        _logger.LogInformation("Session manifest ready: {SessionId}", e.SessionId);
        SessionManifestReady?.Invoke(this, e);
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _adapter.FrameReady -= OnFrameReady;
        _adapter.MarkerEmitted -= OnMarkerEmitted;
        _adapter.SessionManifestReady -= OnSessionManifestReady;
    }
}
