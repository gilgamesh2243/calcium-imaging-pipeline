import type { QCState } from "@/lib/types";

const colours: Record<QCState, string> = {
  GREEN: "bg-green-500",
  YELLOW: "bg-yellow-400",
  RED: "bg-red-500",
  UNKNOWN: "bg-gray-500",
};

const labels: Record<QCState, string> = {
  GREEN: "OK",
  YELLOW: "Warning",
  RED: "Alert",
  UNKNOWN: "Unknown",
};

export function StatusBadge({ state }: { state: QCState }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold text-white ${colours[state]}`}
    >
      <span className="h-2 w-2 rounded-full bg-white/70" />
      {labels[state]}
    </span>
  );
}
