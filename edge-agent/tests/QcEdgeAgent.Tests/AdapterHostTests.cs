using Xunit;
using Microsoft.Extensions.Logging.Abstractions;
using QcAdapterSdk;
using QcEdgeAgent;
using SimulatedAdapter;

namespace QcEdgeAgent.Tests;

public class AdapterHostTests
{
    private static AdapterConfig MakeConfig() => new(
        LabId: "test-lab",
        RigId: "rig-1",
        Fps: 10f,
        Width: 64,
        Height: 64,
        BitDepth: 16,
        Modality: "2p-calcium",
        Extra: new Dictionary<string, string>());

    private static SessionPlan MakePlan() => new(
        SessionId: "test-session-001",
        ConditionGroup: "test",
        ExpectedBaselineSeconds: 3f,
        ExpectedOnsetMinSeconds: 1f,
        ExpectedOnsetMaxSeconds: 10f,
        ExpectedMarkers: ["DRUG_ON"],
        PlanMeta: new Dictionary<string, string>());

    [Fact]
    public async Task AdapterHost_ReceivesFrames_InRingBuffer()
    {
        var adapter = new SimulatedFrameSourceAdapter(
            NullLogger<SimulatedFrameSourceAdapter>.Instance);
        var buf = new RingBuffer<FrameEventArgs>(300);
        using var host = new AdapterHost(adapter, buf, NullLogger<AdapterHost>.Instance);

        var config = MakeConfig();
        var plan = MakePlan();

        await adapter.InitializeAsync(config);
        await adapter.StartSessionAsync(plan);

        // Wait for at least 5 frames
        var deadline = DateTime.UtcNow.AddSeconds(5);
        while (buf.Count < 5 && DateTime.UtcNow < deadline)
            await Task.Delay(50);

        await adapter.StopSessionAsync();

        Assert.True(buf.Count >= 1, "Expected at least 1 frame in the buffer");
    }

    [Fact]
    public async Task AdapterHost_SessionManifestEvent_Fires()
    {
        var adapter = new SimulatedFrameSourceAdapter(
            NullLogger<SimulatedFrameSourceAdapter>.Instance);
        var buf = new RingBuffer<FrameEventArgs>(300);
        using var host = new AdapterHost(adapter, buf, NullLogger<AdapterHost>.Instance);

        SessionManifestEventArgs? received = null;
        host.SessionManifestReady += (_, e) => received = e;

        await adapter.InitializeAsync(MakeConfig());
        await adapter.StartSessionAsync(MakePlan());
        await Task.Delay(200);
        await adapter.StopSessionAsync();

        Assert.NotNull(received);
        Assert.Equal("test-session-001", received!.SessionId);
    }

    [Fact]
    public void StreamerClient_DoesNotThrow_WhenCoreUnreachable()
    {
        var buf = new RingBuffer<FrameEventArgs>(10);
        using var streamer = new StreamerClient(
            buf,
            NullLogger<StreamerClient>.Instance,
            endpoint: "http://localhost:19999" // nothing listening here
        );

        // Enqueue some fake frames
        for (int i = 0; i < 5; i++)
            buf.Enqueue(new FrameEventArgs("s1", (ulong)i, i * 1000L, 0, new byte[64], 8, 8, 16));

        // Start + immediate stop – should not throw
        streamer.Start();
        Thread.Sleep(200);
        streamer.Stop();
    }
}
