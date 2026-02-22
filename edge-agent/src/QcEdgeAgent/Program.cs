using Microsoft.Extensions.Logging;
using QcAdapterSdk;
using QcEdgeAgent;

// ─── Bootstrap ────────────────────────────────────────────────────────────────
using var logFactory = LoggerFactory.Create(b => b.AddConsole());
var logger = logFactory.CreateLogger<Program>();

logger.LogInformation("QC Edge Agent starting...");

// Parse endpoint from args or env
var endpoint = args.Length > 0 ? args[0]
    : Environment.GetEnvironmentVariable("QC_CORE_ENDPOINT") ?? "http://localhost:50051";

var lab = Environment.GetEnvironmentVariable("QC_LAB_ID") ?? "default-lab";
var rig = Environment.GetEnvironmentVariable("QC_RIG_ID") ?? "default-rig";

// ─── Adapter selection ────────────────────────────────────────────────────────
var adapterName = Environment.GetEnvironmentVariable("QC_ADAPTER") ?? "simulated";
IFrameSourceAdapter adapter = adapterName.ToLowerInvariant() switch
{
    "hotfolder" => new HotFolderAdapter.HotFolderFrameSourceAdapter(
        logFactory.CreateLogger<HotFolderAdapter.HotFolderFrameSourceAdapter>()),
    _ => new SimulatedAdapter.SimulatedFrameSourceAdapter(
        logFactory.CreateLogger<SimulatedAdapter.SimulatedFrameSourceAdapter>()),
};

// ─── Ring buffer (default: 10 s at 30 fps = 300 frames) ──────────────────────
var fps = float.Parse(Environment.GetEnvironmentVariable("QC_FPS") ?? "30");
var bufferSeconds = int.Parse(Environment.GetEnvironmentVariable("QC_BUFFER_SECONDS") ?? "10");
var bufferCapacity = (int)(fps * bufferSeconds);
var ringBuffer = new RingBuffer<FrameEventArgs>(bufferCapacity);

// ─── Host + streamer ──────────────────────────────────────────────────────────
var adapterHost = new AdapterHost(
    adapter,
    ringBuffer,
    logFactory.CreateLogger<AdapterHost>());

var streamer = new StreamerClient(
    ringBuffer,
    logFactory.CreateLogger<StreamerClient>(),
    endpoint);

// ─── Wire events ──────────────────────────────────────────────────────────────
adapterHost.MarkerEmitted += (_, e) =>
    logger.LogInformation("Marker event: {Type} = {Value}", e.MarkerType, e.Value);

adapterHost.SessionManifestReady += (_, e) =>
    logger.LogInformation("Session started: {SessionId}", e.SessionId);

// ─── Initialise adapter ───────────────────────────────────────────────────────
var config = new AdapterConfig(
    LabId: lab,
    RigId: rig,
    Fps: fps,
    Width: int.Parse(Environment.GetEnvironmentVariable("QC_WIDTH") ?? "512"),
    Height: int.Parse(Environment.GetEnvironmentVariable("QC_HEIGHT") ?? "512"),
    BitDepth: 16,
    Modality: "2p-calcium",
    Extra: new Dictionary<string, string>());

using var cts = new CancellationTokenSource();
Console.CancelKeyPress += (_, e) => { e.Cancel = true; cts.Cancel(); };

await adapter.InitializeAsync(config, cts.Token);

var plan = new SessionPlan(
    SessionId: $"session-{DateTimeOffset.UtcNow:yyyyMMddHHmmss}",
    ConditionGroup: "default",
    ExpectedBaselineSeconds: 30f,
    ExpectedOnsetMinSeconds: 5f,
    ExpectedOnsetMaxSeconds: 60f,
    ExpectedMarkers: ["DRUG_ON"],
    PlanMeta: new Dictionary<string, string>());

streamer.Start();
await adapter.StartSessionAsync(plan, cts.Token);

logger.LogInformation("Streaming to {Endpoint}. Press Ctrl+C to stop.", endpoint);

try
{
    await Task.Delay(Timeout.Infinite, cts.Token);
}
catch (OperationCanceledException) { }

await adapter.StopSessionAsync();
streamer.Stop();
logger.LogInformation("Edge agent stopped. Frames sent: {Sent}, Dropped: {Dropped}",
    streamer.FramesSent, streamer.FramesDropped);
