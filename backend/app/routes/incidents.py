"""FastAPI endpoints for VeriOps Incident Investigation Core."""

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.incident import (
    EvidenceBundleResponse,
    IncidentSummary,
    IncidentTimelineResponse,
    ServiceDependencyGraphResponse,
)
from app.schemas.investigation import (
    ApprovalRequest,
    DiagnosticExecutionRequest,
    EscalateRequest,
    InvestigationStateResponse,
    InvestigationTrackerResponse,
    RecoveryExecutionRequest,
)
from app.services import incident_service, investigation_orchestrator
from app.services.auth_dependencies import get_current_user

router = APIRouter(prefix="/api/v1/incidents", tags=["Incidents & Investigation"])


@router.post(
    "/seed-demo",
    response_model=IncidentSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Seed or reset canonical demo incident",
    description="Seeds the deterministic multi-source incident telemetry dataset for demonstration.",
)
async def seed_demo(
    scenario_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentSummary:
    """Seed or update the canonical demo incident and return its summary."""
    incident = await incident_service.seed_demo_incident(
        db, current_user_id=current_user.id, target_scenario_id=scenario_id
    )
    await investigation_orchestrator.reset_investigation(db, incident.id)
    summary = await incident_service.get_incident_summary(db, incident.id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve seeded incident summary.",
        )
    return summary


@router.get(
    "",
    response_model=list[IncidentSummary],
    status_code=status.HTTP_200_OK,
    summary="List all investigated incidents",
)
async def list_all_incidents(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[IncidentSummary]:
    """Retrieve list of incidents with evidence counts."""
    return await incident_service.list_incidents(db, limit=limit)


@router.get(
    "/{incident_id}",
    response_model=IncidentSummary,
    status_code=status.HTTP_200_OK,
    summary="Get incident summary",
)
async def get_incident(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentSummary:
    """Retrieve summary for a specific incident."""
    summary = await incident_service.get_incident_summary(db, incident_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )
    return summary


@router.get(
    "/{incident_id}/timeline",
    response_model=IncidentTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chronologically ordered incident timeline",
    description="Returns normalized multi-source evidence ordered strictly by event_time ASC.",
)
async def get_timeline(
    incident_id: uuid.UUID,
    source_type: str | None = Query(default=None, description="Filter by normalized source type"),
    severity: str | None = Query(default=None, description="Filter by event severity"),
    service_name: str | None = Query(default=None, description="Filter by originating service"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> IncidentTimelineResponse:
    """Retrieve chronologically ordered normalized evidence timeline."""
    timeline = await incident_service.get_incident_timeline(
        db,
        incident_id=incident_id,
        source_type=source_type,
        severity=severity,
        service_name=service_name,
    )
    if not timeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )
    return timeline


@router.get(
    "/{incident_id}/graph",
    response_model=ServiceDependencyGraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Get service dependency graph",
    description="Returns topological dependency graph with health metrics and evidence links.",
)
async def get_graph(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ServiceDependencyGraphResponse:
    """Retrieve dynamic service dependency graph for an incident."""
    graph = await incident_service.get_service_dependency_graph(db, incident_id)
    if not graph:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )
    return graph


@router.get(
    "/{incident_id}/evidence-bundle",
    response_model=EvidenceBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get traceable evidence bundle manifest",
    description="Returns versioned, traceable manifest of all correlated evidence for agent investigation.",
)
async def get_bundle(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvidenceBundleResponse:
    """Retrieve versioned evidence bundle manifest."""
    bundle = await incident_service.get_evidence_bundle(db, incident_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )
    return bundle


# =========================================================================
# VeriOps Phase 2: Autonomous Investigation Agent Endpoints
# =========================================================================

@router.get(
    "/{incident_id}/investigation",
    response_model=InvestigationStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active investigation state",
    description="Retrieves current stage, hypotheses, confidence metrics, and diagnostic tool history.",
)
async def get_investigation_state(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestigationStateResponse:
    """Retrieve or initialize active investigation state."""
    try:
        return await investigation_orchestrator.get_or_initialize_investigation(db, incident_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{incident_id}/investigation/diagnose",
    response_model=InvestigationStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Run next diagnostic tool in investigation cycle",
    description="Executes network-first or targeted diagnostic tool and adjusts hypothesis confidence.",
)
async def run_diagnostic_round(
    incident_id: uuid.UUID,
    request: DiagnosticExecutionRequest = DiagnosticExecutionRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestigationStateResponse:
    """Execute diagnostic step and update hypothesis confidence."""
    try:
        return await investigation_orchestrator.execute_diagnostic_step(
            db=db,
            incident_id=incident_id,
            tool_name=request.tool_name,
            target_service=request.target_service,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{incident_id}/investigation/approve",
    response_model=InvestigationStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject formulated recovery plan",
    description="Human operator approval barrier required prior to executing simulated recovery.",
)
async def process_approval(
    incident_id: uuid.UUID,
    request: ApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestigationStateResponse:
    """Process human approval or rejection."""
    try:
        return await investigation_orchestrator.submit_approval_decision(
            db=db,
            incident_id=incident_id,
            decision=request.decision,
            notes=request.notes,
            approver_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{incident_id}/investigation/execute-recovery",
    response_model=InvestigationStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute approved recovery and verify telemetry",
    description="Runs simulated recovery action and runs post-recovery verification loop.",
)
async def execute_recovery(
    incident_id: uuid.UUID,
    request: RecoveryExecutionRequest = RecoveryExecutionRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestigationStateResponse:
    """Execute recovery and verify health criteria."""
    try:
        return await investigation_orchestrator.execute_recovery_and_verify(
            db=db,
            incident_id=incident_id,
            force_verification_failure=request.force_verification_failure,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{incident_id}/investigation/reset",
    response_model=InvestigationStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset investigation state for repeatable demo",
)
async def reset_investigation_state(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestigationStateResponse:
    """Reset investigation state back to initial."""
    try:
        return await investigation_orchestrator.reset_investigation(db, incident_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{incident_id}/investigation/escalate",
    response_model=InvestigationStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Escalate incident to human SRE team",
)
async def escalate_to_human(
    incident_id: uuid.UUID,
    request: EscalateRequest = EscalateRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestigationStateResponse:
    """Escalate incident to human engineering team."""
    try:
        return await investigation_orchestrator.escalate_investigation(
            db=db, incident_id=incident_id, reason=request.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{incident_id}/investigation/tracker",
    response_model=InvestigationTrackerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get persistent 13-stage investigation tracker",
    description="Returns deterministic milestone progress, timestamps, evidence references, and hardware device impact mapping.",
)
async def get_investigation_tracker_state(
    incident_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestigationTrackerResponse:
    """Retrieve persistent 13-stage investigation tracker with device mapping."""
    try:
        return await investigation_orchestrator.get_investigation_tracker(db, incident_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))



