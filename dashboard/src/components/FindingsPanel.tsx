import type { Finding } from "@/lib/types";

const findingColour: Record<string, string> = {
  FLOW_DELAY: "border-orange-500 bg-orange-950",
  BASELINE_DRIFT: "border-yellow-500 bg-yellow-950",
  MOTION: "border-blue-500 bg-blue-950",
  BLEACH: "border-purple-500 bg-purple-950",
  SATURATION: "border-red-500 bg-red-950",
  FOCUS_DRIFT: "border-pink-500 bg-pink-950",
  MARKER_MISSING: "border-gray-500 bg-gray-800",
};

function confidenceBar(confidence: number) {
  const pct = Math.round(confidence * 100);
  const colour =
    confidence > 0.7 ? "bg-red-500" : confidence > 0.4 ? "bg-yellow-400" : "bg-green-500";
  return (
    <div className="mt-1 h-1.5 w-full rounded-full bg-gray-700">
      <div className={`h-1.5 rounded-full ${colour}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function FindingsPanel({ findings }: { findings: Finding[] }) {
  if (findings.length === 0)
    return <p className="text-gray-500 text-sm italic">No findings.</p>;

  return (
    <ul className="space-y-3">
      {findings.map((f, i) => (
        <li
          key={i}
          className={`rounded-lg border-l-4 p-3 ${findingColour[f.type] ?? "border-gray-500 bg-gray-800"}`}
        >
          <div className="flex items-center justify-between">
            <span className="font-semibold text-sm">{f.type.replace(/_/g, " ")}</span>
            <span className="text-xs text-gray-300">{Math.round(f.confidence * 100)}%</span>
          </div>
          {confidenceBar(f.confidence)}
          <p className="mt-1 text-xs text-gray-300">{f.summary}</p>
          {f.evidence && (
            <p className="mt-0.5 text-xs text-gray-500">
              Frames {f.evidence.frame_start}–{f.evidence.frame_end}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
