"""Pydantic schemas for VeriOps Phase 2: Network-First Investigation Agent."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class InvestigationStage(str, Enum):
    INITIALIZING = "INITIALIZING"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"
    DIAGNOSTIC_EXECUTION = "DIAGNOSTIC_EXECUTION"
    CONFIDENCE_UPDATE = "CONFIDENCE_UPDATE"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
    RECOVERY_PLANNING = "RECOVERY_PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RECOVERY_EXECUTION = "RECOVERY_EXECUTION"
    VERIFICATION = "VERIFICATION"
    RESOLVED = "RESOLVED"
    REPLANNING = "REPLANNING"


class IncidentClassification(str, Enum):
    NETWORK = "network"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    MIXED = "mixed"


class HypothesisStatus(str, Enum):
    OPEN = "open"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    REJECTED = "rejected"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Hypothesis(BaseModel):
    """Competing explanation for root cause with explicit evidence links."""
    id: str = Field(..., description="Unique hypothesis identifier (e.g. HYP-01)")
    title: str = Field(..., description="Short descriptive hypothesis title")
    explanation: str = Field(..., description="Detailed mechanism of failure")
    category: str = Field(..., description="network, software, database, infrastructure, deployment")
    supporting_evidence_ids: list[UUID] = Field(default_factory=list)
    contradicting_evidence_ids: list[UUID] = Field(default_factory=list)
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence metric 0.0 - 1.0")
    confidence_rationale: str = Field(..., description="Justification for confidence level")
    status: HypothesisStatus = Field(default=HypothesisStatus.OPEN)
    suspected_components: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DiagnosticToolCall(BaseModel):
    """Record of a diagnostic tool run by the investigation agent."""
    call_id: str
    tool_name: str
    category: str = Field(..., description="network, application, database, infrastructure, deployment_config")
    round: int = Field(default=1, description="Investigation iteration round (1-3)")
    target_service: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    simulated_output: dict[str, Any] = Field(default_factory=dict)
    interpreted_insight: str
    executed_at: datetime
    simulated: bool = Field(default=True)

    model_config = ConfigDict(from_attributes=True)


class RecoveryPlan(BaseModel):
    """Safely formulated recovery plan requiring explicit human approval."""
    action_id: str
    action_name: str
    action_type: str = Field(..., description="config_revert, pool_scaling, pod_restart, hardware_inspection")
    rationale: str
    expected_signal: str
    risk_level: RiskLevel
    affected_services: list[str] = Field(default_factory=list)
    rollback_plan: str
    requires_human_approval: bool = True
    is_approved: bool | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_notes: str | None = None
    executed: bool = False
    simulated: bool = True

    model_config = ConfigDict(from_attributes=True)


class VerificationResult(BaseModel):
    """Post-recovery health check comparing before vs after telemetry."""
    verified: bool
    pre_recovery_metrics: dict[str, Any] = Field(default_factory=dict)
    post_recovery_metrics: dict[str, Any] = Field(default_factory=dict)
    checks: list[dict[str, Any]] = Field(default_factory=list)
    outcome_summary: str
    completed_at: datetime
    simulated: bool = True

    model_config = ConfigDict(from_attributes=True)


class InvestigationStateResponse(BaseModel):
    """Complete serialized state of the active incident investigation."""
    incident_id: UUID
    current_stage: InvestigationStage
    current_round: int
    max_rounds: int = 3
    classification: IncidentClassification
    hypotheses: list[Hypothesis]
    leading_hypothesis_id: str | None = None
    tool_history: list[DiagnosticToolCall] = Field(default_factory=list)
    available_next_tools: list[str] = Field(default_factory=list)
    recovery_plan: RecoveryPlan | None = None
    verification_result: VerificationResult | None = None
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    simulated: bool = True

    model_config = ConfigDict(from_attributes=True)


class DiagnosticExecutionRequest(BaseModel):
    """Request payload to invoke a diagnostic tool through the orchestrator."""
    tool_name: str | None = Field(default=None, description="Optional specific tool name to run. If null, orchestrator decides.")
    target_service: str | None = None


class ApprovalRequest(BaseModel):
    """Payload to approve or reject a proposed recovery plan."""
    decision: str = Field(..., description="'approve' or 'reject'")
    notes: str | None = Field(default=None, description="Human operator notes or feedback")


class RecoveryExecutionRequest(BaseModel):
    """Payload to trigger execution of approved recovery action."""
    force_verification_failure: bool = Field(
        default=False,
        description="Demo flag to trigger verification failure and demonstrate replanning cycle."
    )


class EscalateRequest(BaseModel):
    """Payload to escalate active incident to human on-call team."""
    reason: str | None = Field(
        default="Automated resolution inconclusive. Escalated to Tier 3 SRE on-call team.",
        description="Reason for human escalation"
    )


# =========================================================================
# VeriOps Final MVP: Persistent Investigation Tracker & Hardware Impact
# =========================================================================

class TrackerStageStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    REPLANNING = "REPLANNING"


class TrackerStageEvent(BaseModel):
    """Individual milestone in the 13-stage autonomous investigation tracker."""
    stage_id: int = Field(..., ge=1, le=13, description="Canonical 1-13 stage number")
    stage_key: str = Field(..., description="Unique slug for the stage")
    stage_name: str = Field(..., description="Human-readable stage title")
    category: str = Field(..., description="investigation, diagnostics, recovery, verification")
    status: TrackerStageStatus = Field(default=TrackerStageStatus.PENDING)
    timestamp: datetime | None = None
    summary: str = Field(..., description="Short summary of what occurred in this stage")
    details: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[UUID] = Field(default_factory=list)
    tool_name: str | None = None
    simulated: bool = True

    model_config = ConfigDict(from_attributes=True)


class HardwareDeviceImpact(BaseModel):
    """Mapping of suspected or inspected physical network devices to services."""
    device_name: str
    device_type: str
    ip_address: str
    location: str
    status: str
    health_summary: dict[str, Any] = Field(default_factory=dict)
    impacted_services: list[str] = Field(default_factory=list)
    technician_recommendation: str | None = None
    simulated: bool = True


class InvestigationTrackerResponse(BaseModel):
    """Complete persistent tracker progress across all 13 canonical stages."""
    incident_id: UUID
    current_stage_id: int
    current_stage_name: str
    overall_status: str
    iteration_round: int
    elapsed_seconds: int
    stages: list[TrackerStageEvent]
    device_mapping: list[HardwareDeviceImpact] = Field(default_factory=list)
    summary_counts: dict[str, int] = Field(default_factory=dict)
    simulated: bool = True

    model_config = ConfigDict(from_attributes=True)


