namespace QcAdapterSdk;

/// <summary>Describes adapter capabilities.</summary>
public record AdapterCapabilities(
    bool SupportsLiveMode,
    bool SupportsReplay,
    bool SupportsHotFolder,
    string[] SupportedModalities);

/// <summary>Per-lab/rig adapter configuration.</summary>
public record AdapterConfig(
    string LabId,
    string RigId,
    float Fps,
    int Width,
    int Height,
    int BitDepth,
    string Modality,
    Dictionary<string, string> Extra);

/// <summary>Session plan from the operator / LIMS.</summary>
public record SessionPlan(
    string SessionId,
    string ConditionGroup,
    float ExpectedBaselineSeconds,
    float ExpectedOnsetMinSeconds,
    float ExpectedOnsetMaxSeconds,
    List<string> ExpectedMarkers,
    Dictionary<string, string> PlanMeta);

/// <summary>Raw frame payload.</summary>
public record FrameEventArgs(
    string SessionId,
    ulong FrameIndex,
    long TimestampMonoNs,
    uint ChannelId,
    byte[] Pixels,
    int Width,
    int Height,
    int BitDepth);

/// <summary>Marker / event from acquisition software.</summary>
public record MarkerEventArgs(
    string SessionId,
    long TimestampMonoNs,
    string MarkerType,
    string Value,
    Dictionary<string, string> Meta);

/// <summary>Session manifest produced at acquisition start.</summary>
public record SessionManifestEventArgs(
    string SessionId,
    string LabId,
    string RigId,
    string Modality,
    float Fps,
    int Width,
    int Height,
    List<ChannelInfo> Channels,
    Dictionary<string, string> AcquisitionMeta,
    Dictionary<string, string> PlanMeta,
    string AdapterName,
    string AdapterVersion);

/// <summary>Single imaging channel descriptor.</summary>
public record ChannelInfo(uint ChannelId, string Name, float Wavelength, int BitDepth);
