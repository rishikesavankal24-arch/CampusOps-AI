/**
 * TypeScript types for VeriOps Incident Investigation Core.
 */

export type SourceType =
  | "application_log"
  | "infrastructure_log"
  | "metric"
  | "trace"
  | "alert"
  | "deployment"
  | "configuration"
  | "support_ticket"
  | "previous_incident";

export type EventSeverity = "info" | "warning" | "error" | "critical";

export interface NormalizedEvidenceItem {
  evidence_id: string;
  incident_id: string;
  source_type: SourceType;
  service_name: string;
  event_time: string;
  ingest_time: string;
  severity: EventSeverity;
  title: string;
  content: string;
  details: Record<string, unknown>;
  correlation_id: string | null;
  related_service: string | null;
  simulated: boolean;
  source_metadata: Record<string, unknown>;
}

export interface IncidentSummary {
  id: string;
  title: string;
  description: string;
  status: "open" | "investigating" | "resolved" | "closed";
  priority: "low" | "medium" | "high" | "critical";
  category: string;
  created_at: string;
  event_start?: string | null;
  evidence_count: number;
  affected_services_count: number;
  simulated: boolean;
}

export interface IncidentTimelineResponse {
  incident_id: string;
  incident_title: string;
  severity: string;
  status: string;
  total_events: number;
  filtered_events: number;
  time_window: {
    start: string | null;
    end: string | null;
  };
  events: NormalizedEvidenceItem[];
}

export interface ServiceNode {
  id: string;
  name: string;
  service_type: "frontend" | "gateway" | "microservice" | "database" | "cache" | "idp";
  status: "healthy" | "degraded" | "critical" | "unknown";
  impact: "none" | "low" | "medium" | "high" | "root_suspect";
  metrics_summary: Record<string, unknown>;
  supporting_evidence_ids: string[];
}

export interface ServiceEdge {
  source: string;
  target: string;
  relationship: string;
  protocol: string;
  is_degraded: boolean;
}

export interface ServiceDependencyGraphResponse {
  incident_id: string;
  nodes: ServiceNode[];
  edges: ServiceEdge[];
  root_suspects: string[];
  affected_services: string[];
}

export interface EvidenceBundleResponse {
  bundle_id: string;
  bundle_version: string;
  created_at: string;
  incident_id: string;
  incident_title: string;
  time_window: {
    start: string | null;
    end: string | null;
  };
  total_evidence_count: number;
  evidence_references: string[];
  timeline_summary: Array<{
    evidence_id: string;
    event_time: string;
    source_type: string;
    service_name: string;
    severity: string;
    title: string;
    correlation_id: string | null;
  }>;
  affected_services: string[];
  data_quality_notes: string[];
  simulated: boolean;
}
