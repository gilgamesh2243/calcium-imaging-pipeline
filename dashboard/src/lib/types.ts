export type QCState = "GREEN" | "YELLOW" | "RED" | "UNKNOWN";

export interface Finding {
  type: string;
  confidence: number;
  summary: string;
  evidence?: {
    frame_start: number;
    frame_end: number;
    metric_trace_ids: string[];
  };
}

export interface QCStatus {
  session_id: string;
  t_eval_mono_ns: number;
  state: QCState;
  risk_score: number;
  top_findings: Finding[];
}

export interface Session {
  session_id: string;
  lab_id: string;
  rig_id: string;
  modality: string;
  started_at: string;
}
