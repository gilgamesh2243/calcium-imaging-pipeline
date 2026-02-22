namespace QcAdapterSdk;

/// <summary>
/// Stable interface every lab adapter must implement.
/// Never throws into the caller – use events and logging for errors.
/// </summary>
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
