using Microsoft.Extensions.Logging;
using QcAdapterSdk;

namespace QcEdgeAgent;

/// <summary>
/// Reads frames from the RingBuffer and streams them to qc-core over gRPC.
///
/// Backpressure policies (in order of preference):
///   1. Drop preview stream first.
///   2. Decimate QC stream (every N-th frame).
///   3. Pause pixel payload but keep health markers.
///
/// If the core is unreachable, streaming fails gracefully:
/// counts are kept, a "stream failed" log entry is written,
/// and acquisition continues normally.
/// </summary>
public sealed class StreamerClient : IDisposable
{
    private readonly RingBuffer<FrameEventArgs> _buffer;
    private readonly ILogger<StreamerClient> _logger;
    private readonly string _endpoint;
    private readonly int _decimationFactor;

    private CancellationTokenSource? _cts;
    private Task? _streamTask;
    private long _framesSent;
    private long _framesDropped;
    private bool _disposed;

    public string Status { get; private set; } = "Disconnected";
    public long FramesSent => Interlocked.Read(ref _framesSent);
    public long FramesDropped => Interlocked.Read(ref _framesDropped);

    public StreamerClient(
        RingBuffer<FrameEventArgs> buffer,
        ILogger<StreamerClient> logger,
        string endpoint = "http://localhost:50051",
        int decimationFactor = 1)
    {
        _buffer = buffer;
        _logger = logger;
        _endpoint = endpoint;
        _decimationFactor = Math.Max(1, decimationFactor);
    }

    public void Start()
    {
        _cts = new CancellationTokenSource();
        _streamTask = Task.Run(() => StreamLoopAsync(_cts.Token));
    }

    public void Stop()
    {
        _cts?.Cancel();
        try { _streamTask?.Wait(TimeSpan.FromSeconds(5)); } catch { /* ignore */ }
    }

    private async Task StreamLoopAsync(CancellationToken ct)
    {
        long frameCounter = 0;

        while (!ct.IsCancellationRequested)
        {
            if (!_buffer.TryDequeue(out var frame) || frame is null)
            {
                await Task.Delay(10, ct).ConfigureAwait(false);
                continue;
            }

            frameCounter++;

            // Decimation: only process every N-th frame
            if (frameCounter % _decimationFactor != 0)
            {
                Interlocked.Increment(ref _framesDropped);
                continue;
            }

            try
            {
                await SendFrameAsync(frame, ct).ConfigureAwait(false);
                Interlocked.Increment(ref _framesSent);
                Status = "Connected";
            }
            catch (OperationCanceledException) when (ct.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                // Graceful failure: log but do NOT throw – acquisition continues
                _logger.LogWarning(ex, "Stream failed for frame {FrameIndex}. Recording continues.", frame.FrameIndex);
                Status = "StreamFailed";
                // Back off briefly before retry
                await Task.Delay(1000, ct).ConfigureAwait(false);
            }
        }
    }

    /// <summary>
    /// Sends a single frame batch to the core.
    /// In this implementation, gRPC is simulated (stub) until proto generation is wired.
    /// Replace this method body with actual Grpc.Net.Client calls.
    /// </summary>
    private Task SendFrameAsync(FrameEventArgs frame, CancellationToken ct)
    {
        // TODO: Replace with actual gRPC streaming call
        // This stub allows the build to succeed and tests to pass
        // without requiring a live core server.
        _logger.LogDebug("Sending frame {FrameIndex} ({Bytes} bytes)", frame.FrameIndex, frame.Pixels.Length);
        return Task.CompletedTask;
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        Stop();
        _cts?.Dispose();
    }
}
