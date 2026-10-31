"""Pydantic schemas for VeriOps Incident Investigation Core."""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class NormalizedEvidenceItem(BaseModel):
    """Normalized evidence event supporting multi-source correlation."""
    evidence_id: UUID = Field(..., description="Unique evidence record identifier")
    incident_id: UUID = Field(..., description="Associated incident identifier")
    source_type: str = Field(
        ...,
        description="Source classification: application_log, infrastructure_log, metric, trace, alert, deployment, configuration, support_ticket, previous_incident",
    )
    service_name: str = Field(..., description="Originating service or component name")
    event_time: datetime = Field(..., description="Time when the event occurred in the target environment")
    ingest_time: datetime = Field(..., description="Time when the event was ingested into VeriOps")
    severity: str = Field(..., description="Event severity: info, warning, error, critical")
    title: str = Field(..., description="Concise event headline")
    content: str = Field(..., description="Full text payload, log line, or trace statement")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured event payload")
    correlation_id: str | None = Field(default=None, description="Distributed correlation ID (trace/request)")
    related_service: str | None = Field(default=None, description="Downstream or upstream dependency reference")
    simulated: bool = Field(default=True, description="True for simulated hackathon test data")
    source_metadata: dict[str, Any] = Field(default_factory=dict, description="Source provenance metadata")

    model_config = ConfigDict(from_attributes=True)


class IncidentSummary(BaseModel):
    """Concise summary of an active or investigated incident."""
    id: UUID
    title: str
    description: str
    status: str
    priority: str
    category: str
    created_at: datetime
    event_start: datetime | None = None
    evidence_count: int = 0
    affected_services_count: int = 0
    simulated: bool = True

    model_config = ConfigDict(from_attributes=True)


class IncidentTimelineResponse(BaseModel):
    """Chronologically sequenced incident timeline response."""
    incident_id: UUID
    incident_title: str
    severity: str
    status: str
    total_events: int
    filtered_events: int
    time_window: dict[str, datetime | None]
    events: list[NormalizedEvidenceItem]


class ServiceNode(BaseModel):
    """Node in the service dependency graph with live telemetry health."""
    id: str = Field(..., description="Unique service identifier (slug)")
    name: str = Field(..., description="Human-readable service title")
    service_type: str = Field(..., description="frontend, gateway, microservice, database, cache, idp")
    status: str = Field(..., description="healthy, degraded, critical, unknown")
    impact: str = Field(..., description="none, low, medium, high, root_suspect")
    metrics_summary: dict[str, Any] = Field(default_factory=dict)
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)


class ServiceEdge(BaseModel):
    """Directional dependency relationship between services."""
    source: str
    target: str
    relationship: str = Field(default="calls")
    protocol: str = Field(default="HTTP/REST")
    is_degraded: bool = False


class ServiceDependencyGraphResponse(BaseModel):
    """Complete service dependency topology with incident impact markers."""
    incident_id: UUID
    nodes: list[ServiceNode]
    edges: list[ServiceEdge]
    root_suspects: list[str]
    affected_services: list[str]


class EvidenceBundleResponse(BaseModel):
    """Traceable, versioned evidence bundle ready for agentic investigation."""
    bundle_id: str
    bundle_version: str = "1.0.0"
    created_at: datetime
    incident_id: UUID
    incident_title: str
    time_window: dict[str, datetime | None]
    total_evidence_count: int
    evidence_references: list[UUID]
    timeline_summary: list[dict[str, Any]]
    affected_services: list[str]
    data_quality_notes: list[str]
    simulated: bool = True

