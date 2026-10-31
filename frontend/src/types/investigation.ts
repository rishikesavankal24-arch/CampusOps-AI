/**
 * TypeScript types for VeriOps Phase 2: Network-First Investigation Agent.
 */

export type InvestigationStage =
  | "INITIALIZING"
  | "EVIDENCE_REVIEW"
  | "HYPOTHESIS_GENERATION"
  | "DIAGNOSTIC_EXECUTION"
  | "CONFIDENCE_UPDATE"
  | "ROOT_CAUSE_ANALYSIS"
  | "RECOVERY_PLANNING"
  | "AWAITING_APPROVAL"
  | "RECOVERY_EXECUTION"
  | "VERIFICATION"
  | "RESOLVED"
  | "REPLANNING";

export type IncidentClassification = "network" | "hardware" | "software" | "mixed";

export type HypothesisStatus = "open" | "supported" | "weakened" | "rejected";

export type RiskLevel = "low" | "medium" | "high";

export interface Hypothesis {
  id: string;
  title: string;
  explanation: string;
  category: string;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  confidence_score: number;
  confidence_rationale: string;
  status: HypothesisStatus;
  suspected_components: string[];
}

export interface DiagnosticToolCall {
  call_id: string;
  tool_name: string;
  category: string;
  round: number;
  target_service: string;
  parameters: Record<string, unknown>;
  simulated_output: Record<string, unknown>;
  interpreted_insight: string;
  executed_at: string;
  simulated: boolean;
}

export interface RecoveryPlan {
  action_id: string;
  action_name: string;
  action_type: string;
  rationale: string;
  expected_signal: string;
  risk_level: RiskLevel;
  affected_services: string[];
  rollback_plan: string;
  requires_human_approval: boolean;
  is_approved: boolean | null;
  approved_by: string | null;
  approved_at: string | null;
  approval_notes: string | null;
  executed: boolean;
  simulated: boolean;
}

export interface VerificationResult {
  verified: boolean;
  pre_recovery_metrics: Record<string, unknown>;
  post_recovery_metrics: Record<string, unknown>;
  checks: Array<{
    metric: string;
    threshold: string;
    value: string;
    passed: boolean;
  }>;
  outcome_summary: string;
  completed_at: string;
  simulated: boolean;
}

export interface InvestigationStateResponse {
  incident_id: string;
  current_stage: InvestigationStage;
  current_round: number;
  max_rounds: number;
  classification: IncidentClassification;
  hypotheses: Hypothesis[];
  leading_hypothesis_id: string | null;
  tool_history: DiagnosticToolCall[];
  available_next_tools: string[];
  recovery_plan: RecoveryPlan | null;
  verification_result: VerificationResult | null;
  audit_log: Array<{
    timestamp: string;
    event: string;
    [key: string]: unknown;
  }>;
  simulated: boolean;
}

export type TrackerStageStatus =
  | "PENDING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "BLOCKED"
  | "REPLANNING";

export interface TrackerStageEvent {
  stage_id: number;
  stage_key: string;
  stage_name: string;
  category: "investigation" | "diagnostics" | "recovery" | "verification";
  status: TrackerStageStatus;
  timestamp: string | null;
  summary: string;
  details: Record<string, unknown>;
  evidence_ids: string[];
  tool_name: string | null;
  simulated: boolean;
}

export interface HardwareDeviceImpact {
  device_name: string;
  device_type: string;
  ip_address: string;
  location: string;
  status: string;
  health_summary: Record<string, unknown>;
  impacted_services: string[];
  technician_recommendation: string | null;
  simulated: boolean;
}

export interface InvestigationTrackerResponse {
  incident_id: string;
  current_stage_id: number;
  current_stage_name: string;
  overall_status: string;
  iteration_round: number;
  elapsed_seconds: number;
  stages: TrackerStageEvent[];
  device_mapping: HardwareDeviceImpact[];
  summary_counts: Record<string, number>;
  simulated: boolean;
}


