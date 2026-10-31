"""VeriOps Phase 2: Lightweight Investigation Orchestrator & State Machine.

Manages deterministic, evidence-grounded multi-hypothesis investigation,
network-first diagnostic branching, confidence scoring, human-in-the-loop
approval barriers, and simulated verification loops.
"""

from datetime import datetime, timezone
from typing import Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus
from app.schemas.investigation import (
    DiagnosticToolCall,
    HardwareDeviceImpact,
    Hypothesis,
    HypothesisStatus,
    IncidentClassification,
    InvestigationStage,
    InvestigationStateResponse,
    InvestigationTrackerResponse,
    RecoveryPlan,
    RiskLevel,
    TrackerStageEvent,
    TrackerStageStatus,
    VerificationResult,
)
from app.services import diagnostic_tools
from app.services.incident_service import DEMO_INCIDENT_ID


def _build_initial_hypotheses(incident_id: uuid.UUID) -> list[Hypothesis]:
    """Generate canonical 3 competing hypotheses with supporting evidence references."""
    return [
        Hypothesis(
            id="HYP-01",
            title="Campus Ingress Network / DNS Core Latency Degradation",
            explanation=(
                "Campus network backbone or ingress DNS resolution experiencing packet loss or high latency, "
                "triggering client-side timeout cascades and downstream HTTP 504 errors at the gateway."
            ),
            category="network",
            supporting_evidence_ids=[
                uuid.UUID("a1111111-0000-0000-0000-000000000004"),  # Alert 504
                uuid.UUID("a1111111-0000-0000-0000-000000000008"),  # Metric login failure
                uuid.UUID("a1111111-0000-0000-0000-000000000009"),  # Helpdesk ticket
            ],
            contradicting_evidence_ids=[],
            confidence_score=0.45,
            confidence_rationale="Students observe 504 Gateway Timeouts; could stem from core L3/L4 network drops or DNS delays.",
            status=HypothesisStatus.OPEN,
            suspected_components=["portal-gateway", "switch-core-bldg-a"],
        ),
        Hypothesis(
            id="HYP-02",
            title="PostgreSQL Async Connection Pool Starvation via ConfigMap Reduction",
            explanation=(
                "Database connection pool limit was reduced to 15 in values.yaml. Under peak registration concurrency, "
                "all sessions are exhausted, causing SQLAlchemy async QueuePool timeout errors."
            ),
            category="database",
            supporting_evidence_ids=[
                uuid.UUID("a1111111-0000-0000-0000-000000000001"),  # Config pool_max 15
                uuid.UUID("a1111111-0000-0000-0000-000000000003"),  # Metric DB pool sat
                uuid.UUID("a1111111-0000-0000-0000-000000000005"),  # App log TimeoutError
                uuid.UUID("a1111111-0000-0000-0000-000000000006"),  # Trace 9.8s DB acquisition
                uuid.UUID("a1111111-0000-0000-0000-000000000007"),  # Postgres idle in tx
                uuid.UUID("a1111111-0000-0000-0000-000000000011"),  # Previous postmortem
            ],
            contradicting_evidence_ids=[],
            confidence_score=0.78,
            confidence_rationale="Correlated telemetry reveals 100% pool utilization and explicit QueuePool timeout exceptions.",
            status=HypothesisStatus.OPEN,
            suspected_components=["auth-service", "campusops-db"],
        ),
        Hypothesis(
            id="HYP-03",
            title="Auth-Service v2.4.1 Canary Argon2id Crypto Thread Saturation",
            explanation=(
                "Canary rollout of auth-service:v2.4.1 increased Argon2id memory cost parameter to 64MB, "
                "saturating CPU worker threads during password verification bursts."
            ),
            category="software",
            supporting_evidence_ids=[
                uuid.UUID("a1111111-0000-0000-0000-000000000002"),  # Canary rollout
                uuid.UUID("a1111111-0000-0000-0000-000000000010"),  # Redis session surge
            ],
            contradicting_evidence_ids=[
                uuid.UUID("a1111111-0000-0000-0000-000000000006"),  # Trace shows argon2 is only 380ms vs 9820ms DB
            ],
            confidence_score=0.40,
            confidence_rationale="Recent deployment modified CPU/memory hashing settings right before incident triggered.",
            status=HypothesisStatus.OPEN,
            suspected_components=["auth-service"],
        ),
    ]


async def get_or_initialize_investigation(
    db: AsyncSession, incident_id: uuid.UUID
) -> InvestigationStateResponse:
    """Retrieve active investigation state or initialize default multi-hypothesis state."""
    stmt = select(Incident).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found.")

    raw_state = incident.ai_root_cause or {}
    if raw_state and "current_stage" in raw_state:
        try:
            return InvestigationStateResponse.model_validate(raw_state)
        except Exception:
            pass  # Fall back to initializing clean state

    # Initialize clean Phase 2 investigation state
    hypotheses = _build_initial_hypotheses(incident_id)
    initial_audit = [
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "INVESTIGATION_INITIALIZED",
            "message": "Orchestrator initialized multi-hypothesis investigation. Network-first diagnostic policy engaged.",
        }
    ]

    state = InvestigationStateResponse(
        incident_id=incident_id,
        current_stage=InvestigationStage.HYPOTHESIS_GENERATION,
        current_round=1,
        max_rounds=3,
        classification=IncidentClassification.MIXED,
        hypotheses=hypotheses,
        leading_hypothesis_id="HYP-02",
        tool_history=[],
        available_next_tools=[
            "network_connectivity_diagnostic",
            "application_diagnostics",
            "database_diagnostics",
            "deployment_config_diagnostics",
        ],
        recovery_plan=None,
        verification_result=None,
        audit_log=initial_audit,
        simulated=True,
    )

    incident.ai_root_cause = state.model_dump(mode="json")
    await db.commit()
    return state


async def execute_diagnostic_step(
    db: AsyncSession,
    incident_id: uuid.UUID,
    tool_name: str | None = None,
    target_service: str | None = None,
) -> InvestigationStateResponse:
    """Execute a diagnostic tool round and update hypothesis confidence accordingly."""
    state = await get_or_initialize_investigation(db, incident_id)

    # Determine which tool to execute (Network-first by default in round 1)
    if not tool_name:
        if state.current_round == 1:
            tool_name = "network_connectivity_diagnostic"
        elif state.current_round == 2:
            tool_name = "database_diagnostics"
        else:
            tool_name = "deployment_config_diagnostics"

    now_iso = datetime.now(timezone.utc).isoformat()

    # Execute selected tool from registry
    if tool_name == "network_connectivity_diagnostic":
        tool_call = diagnostic_tools.run_network_connectivity_diagnostic(
            target_service=target_service or "portal-gateway",
            round_num=state.current_round,
        )
        # Network diagnostic passed -> Weaken HYP-01 (Network Outage)
        for h in state.hypotheses:
            if h.id == "HYP-01":
                h.confidence_score = 0.10
                h.status = HypothesisStatus.REJECTED
                h.confidence_rationale = (
                    "DIAGNOSTIC PROVEN FALSE: ICMP ping, DNS (3.8ms), DHCP, and switch telemetry "
                    "confirmed 0% packet loss and 1.2ms latency. Physical network is fully operational."
                )
                h.contradicting_evidence_ids.append(uuid.UUID("a1111111-0000-0000-0000-000000000004"))
            elif h.id == "HYP-02":
                h.confidence_score = 0.88
                h.confidence_rationale = (
                    "Network layer ruled out; upstream latency directly pinpoints database connection pool starvation."
                )

        state.classification = IncidentClassification.SOFTWARE
        state.audit_log.append({
            "timestamp": now_iso,
            "event": "TOOL_EXECUTED",
            "tool": "network_connectivity_diagnostic",
            "insight": tool_call.interpreted_insight,
            "effect": "Weakened HYP-01 (Network) to 0.10 (REJECTED); Elevated HYP-02 (Database Pool) to 0.88.",
        })

    elif tool_name == "database_diagnostics":
        tool_call = diagnostic_tools.run_database_diagnostics(
            target_service=target_service or "campusops-db",
            round_num=state.current_round,
        )
        for h in state.hypotheses:
            if h.id == "HYP-02":
                h.confidence_score = 0.94
                h.status = HypothesisStatus.SUPPORTED
                h.confidence_rationale = (
                    "DIAGNOSTIC CONFIRMED: 15/15 active connections (100% capacity) with 48 threads queued. "
                    "Host CPU is 14% (not hardware saturation); pool limit is primary bottleneck."
                )
            elif h.id == "HYP-03":
                h.confidence_score = 0.22
                h.status = HypothesisStatus.WEAKENED
                h.confidence_rationale = "Crypto hashing accounts for < 4% of request latency; DB wait accounts for 96%."

        state.audit_log.append({
            "timestamp": now_iso,
            "event": "TOOL_EXECUTED",
            "tool": "database_diagnostics",
            "insight": tool_call.interpreted_insight,
            "effect": "Elevated HYP-02 to 0.94 (SUPPORTED); Weakened HYP-03 to 0.22.",
        })

    elif tool_name == "deployment_config_diagnostics":
        tool_call = diagnostic_tools.run_deployment_config_diagnostics(
            target_service=target_service or "auth-service",
            round_num=state.current_round,
        )
        for h in state.hypotheses:
            if h.id == "HYP-02":
                h.confidence_score = 0.98
                h.status = HypothesisStatus.SUPPORTED
                h.confidence_rationale = (
                    "ROOT CAUSE CONFIRMED: GitOps commit a8f912c dropped max_db_pool_connections "
                    "from 50 to 15 prior to peak course registration."
                )

        state.audit_log.append({
            "timestamp": now_iso,
            "event": "TOOL_EXECUTED",
            "tool": "deployment_config_diagnostics",
            "insight": tool_call.interpreted_insight,
            "effect": "Confirmed HYP-02 as Root Cause at 0.98 confidence.",
        })

    else:
        # Generic application fallback diagnostic
        tool_call = diagnostic_tools.run_application_diagnostics(
            target_service=target_service or "auth-service",
            round_num=state.current_round,
        )
        state.audit_log.append({
            "timestamp": now_iso,
            "event": "TOOL_EXECUTED",
            "tool": "application_diagnostics",
            "insight": tool_call.interpreted_insight,
            "effect": "Application traces verified.",
        })

    state.tool_history.append(tool_call)

    # Formulate Recovery Plan when confident (confidence >= 0.85 or round >= 2)
    leading_hyp = max(state.hypotheses, key=lambda h: h.confidence_score)
    state.leading_hypothesis_id = leading_hyp.id

    if leading_hyp.confidence_score >= 0.85 or state.current_round >= 2:
        state.current_stage = InvestigationStage.AWAITING_APPROVAL
        state.recovery_plan = RecoveryPlan(
            action_id="ACT-REVERT-POOL-01",
            action_name="Revert Database Connection Pool Configuration to Baseline (50)",
            action_type="config_revert",
            rationale=(
                "Revert max_db_pool_connections from 15 back to baseline 50 in Helm values.yaml, "
                "and trigger graceful rolling restart of auth-service pods to flush idle-in-transaction sessions."
            ),
            expected_signal=(
                "SQLAlchemy queue depth drops to 0; Gateway P99 latency returns < 400ms; "
                "HTTP 504 error rate drops to < 0.1%."
            ),
            risk_level=RiskLevel.LOW,
            affected_services=["auth-service", "campusops-db", "portal-gateway"],
            rollback_plan="Re-apply commit a8f912c if auth-service fails health probe.",
            requires_human_approval=True,
            is_approved=None,
            executed=False,
            simulated=True,
        )
        state.audit_log.append({
            "timestamp": now_iso,
            "event": "RECOVERY_PLAN_FORMULATED",
            "action": state.recovery_plan.action_name,
            "risk": state.recovery_plan.risk_level.value,
            "status": "Awaiting explicit human approval before execution.",
        })
    else:
        state.current_stage = InvestigationStage.CONFIDENCE_UPDATE
        state.current_round = min(state.current_round + 1, state.max_rounds)

    # Persist state
    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalars().first()
    if incident:
        incident.ai_root_cause = state.model_dump(mode="json")
        await db.commit()

    return state


async def submit_approval_decision(
    db: AsyncSession,
    incident_id: uuid.UUID,
    decision: str,
    notes: str | None = None,
    approver_email: str = "operator@campusops.edu",
) -> InvestigationStateResponse:
    """Process human operator approval or rejection for the formulated recovery plan."""
    state = await get_or_initialize_investigation(db, incident_id)

    if not state.recovery_plan:
        raise ValueError("No recovery plan has been formulated for this incident.")

    now_iso = datetime.now(timezone.utc).isoformat()

    if decision.lower() == "approve":
        state.recovery_plan.is_approved = True
        state.recovery_plan.approved_by = approver_email
        state.recovery_plan.approved_at = datetime.now(timezone.utc)
        state.recovery_plan.approval_notes = notes or "Approved by operator for simulated execution."
        state.current_stage = InvestigationStage.RECOVERY_EXECUTION

        state.audit_log.append({
            "timestamp": now_iso,
            "event": "RECOVERY_PLAN_APPROVED",
            "approver": approver_email,
            "notes": state.recovery_plan.approval_notes,
            "next_step": "Ready for execution and telemetry verification.",
        })
    else:
        state.recovery_plan.is_approved = False
        state.recovery_plan.approval_notes = notes or "Rejected by human operator."
        state.current_stage = InvestigationStage.REPLANNING

        state.audit_log.append({
            "timestamp": now_iso,
            "event": "RECOVERY_PLAN_REJECTED",
            "approver": approver_email,
            "notes": state.recovery_plan.approval_notes,
            "next_step": "Returned to orchestrator for alternative hypothesis exploration.",
        })

    # Persist
    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalars().first()
    if incident:
        incident.ai_root_cause = state.model_dump(mode="json")
        await db.commit()

    return state


async def execute_recovery_and_verify(
    db: AsyncSession,
    incident_id: uuid.UUID,
    force_verification_failure: bool = False,
) -> InvestigationStateResponse:
    """Execute the approved recovery action and run post-recovery telemetry verification."""
    state = await get_or_initialize_investigation(db, incident_id)

    if not state.recovery_plan:
        raise ValueError("No recovery plan available to execute.")

    # Explicit Safety Check: Human approval barrier
    if state.recovery_plan.is_approved is not True:
        raise PermissionError(
            "SAFETY VIOLATION: Recovery execution blocked. Explicit human approval is required."
        )

    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    # 1. Mark simulated recovery action executed
    state.recovery_plan.executed = True
    state.audit_log.append({
        "timestamp": now_iso,
        "event": "SIMULATED_RECOVERY_EXECUTED",
        "action": state.recovery_plan.action_name,
        "applied_changes": [
            "GitOps commit revert applied (values.yaml: database.pool_size = 50)",
            "Rolling pod restart completed for auth-service (3/3 Ready)",
            "Active idle-in-transaction connection handles released",
        ],
    })

    # 2. Generate simulated verification telemetry
    if force_verification_failure:
        # Demonstrate verification failure and replanning
        pre_metrics = {
            "gateway_p99_latency_seconds": 10.82,
            "gateway_504_error_rate": 0.148,
            "db_pool_utilization_pct": 100.0,
            "login_failure_rate": 0.842,
        }
        post_metrics = {
            "gateway_p99_latency_seconds": 9.42,
            "gateway_504_error_rate": 0.115,
            "db_pool_utilization_pct": 94.0,
            "login_failure_rate": 0.720,
        }
        checks = [
            {"metric": "Gateway 504 Rate", "threshold": "< 0.5%", "value": "11.5%", "passed": False},
            {"metric": "P99 Ingress Latency", "threshold": "< 1.2s", "value": "9.42s", "passed": False},
            {"metric": "DB Pool Saturation", "threshold": "< 80%", "value": "94.0%", "passed": False},
        ]
        verification = VerificationResult(
            verified=False,
            pre_recovery_metrics=pre_metrics,
            post_recovery_metrics=post_metrics,
            checks=checks,
            outcome_summary="VERIFICATION FAILED: Error rate (11.5%) remains above SLA threshold (< 0.5%).",
            completed_at=now_utc,
            simulated=True,
        )
        state.verification_result = verification
        state.current_stage = InvestigationStage.REPLANNING

        state.audit_log.append({
            "timestamp": now_iso,
            "event": "VERIFICATION_FAILED",
            "summary": verification.outcome_summary,
            "next_step": "Orchestrator initiated replanning cycle.",
        })

    else:
        # Happy Path Verification PASS
        pre_metrics = {
            "gateway_p99_latency_seconds": 10.82,
            "gateway_504_error_rate": 0.148,
            "db_pool_utilization_pct": 100.0,
            "login_failure_rate": 0.842,
        }
        post_metrics = {
            "gateway_p99_latency_seconds": 0.24,
            "gateway_504_error_rate": 0.0002,
            "db_pool_utilization_pct": 28.0,
            "login_failure_rate": 0.008,
        }
        checks = [
            {"metric": "Gateway 504 Rate", "threshold": "< 0.5%", "value": "0.02%", "passed": True},
            {"metric": "P99 Ingress Latency", "threshold": "< 1.2s", "value": "240ms", "passed": True},
            {"metric": "DB Pool Saturation", "threshold": "< 80%", "value": "28.0%", "passed": True},
            {"metric": "Student Portal Login Success", "threshold": "> 98.0%", "value": "99.2%", "passed": True},
        ]
        verification = VerificationResult(
            verified=True,
            pre_recovery_metrics=pre_metrics,
            post_recovery_metrics=post_metrics,
            checks=checks,
            outcome_summary="VERIFICATION SUCCESS: All SLA criteria satisfied. Incident successfully resolved.",
            completed_at=now_utc,
            simulated=True,
        )
        state.verification_result = verification
        state.current_stage = InvestigationStage.RESOLVED

        state.audit_log.append({
            "timestamp": now_iso,
            "event": "VERIFICATION_PASSED",
            "summary": verification.outcome_summary,
            "status": "INCIDENT_RESOLVED",
        })

    # Persist and update Incident status if verified
    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalars().first()
    if incident:
        incident.ai_root_cause = state.model_dump(mode="json")
        if state.verification_result and state.verification_result.verified:
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = now_utc
            incident.ai_resolution = {
                "action": state.recovery_plan.action_name,
                "verified_at": now_iso,
                "post_metrics": state.verification_result.post_recovery_metrics,
                "simulated": True,
            }
        await db.commit()

    return state


async def reset_investigation(
    db: AsyncSession, incident_id: uuid.UUID
) -> InvestigationStateResponse:
    """Reset investigation state and restore incident to investigating for repeatable demo."""
    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalars().first()
    if not incident:
        raise ValueError(f"Incident {incident_id} not found.")

    incident.ai_root_cause = None
    incident.ai_resolution = None
    incident.status = IncidentStatus.INVESTIGATING
    incident.resolved_at = None
    await db.commit()

    return await get_or_initialize_investigation(db, incident_id)


async def escalate_investigation(
    db: AsyncSession, incident_id: uuid.UUID, reason: str | None = None
) -> InvestigationStateResponse:
    """Escalate unresolved incident to human on-call SRE team and log audit event."""
    state = await get_or_initialize_investigation(db, incident_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    escalation_reason = reason or "Automated investigation inconclusive. Escalated to Tier 3 Platform SRE Team."

    state.current_stage = InvestigationStage.REPLANNING
    state.audit_log.append({
        "timestamp": now_iso,
        "event": "ESCALATED_TO_HUMAN_SRE",
        "reason": escalation_reason,
        "assignee": "Tier 3 Platform Operations (PagerDuty: oncall-sre-lead)",
        "status": "Escalated to human engineers with full correlated evidence package.",
    })

    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalars().first()
    if incident:
        incident.ai_root_cause = state.model_dump(mode="json")
        await db.commit()

    return state


async def get_investigation_tracker(
    db: AsyncSession, incident_id: uuid.UUID
) -> InvestigationTrackerResponse:
    """Compute and return persistent investigation tracker across all 13 canonical stages."""
    state = await get_or_initialize_investigation(db, incident_id)

    # Fetch incident created time for elapsed calculation
    stmt = select(Incident).where(Incident.id == incident_id)
    res = await db.execute(stmt)
    incident = res.scalars().first()

    now_utc = datetime.now(timezone.utc)
    created_at = incident.created_at if incident and incident.created_at else now_utc
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    elapsed_seconds = int((now_utc - created_at).total_seconds())

    # Build 13 canonical tracker stages
    leading_hyp = next((h for h in state.hypotheses if h.id == state.leading_hypothesis_id), None)
    leading_conf = leading_hyp.confidence_score if leading_hyp else 0.78

    has_network_diagnostic = any(t.category == "network" for t in state.tool_history)
    has_supporting_diagnostic = any(t.category in ("database", "deployment_config", "application") for t in state.tool_history)
    plan_exists = state.recovery_plan is not None
    plan_approved = plan_exists and state.recovery_plan.is_approved is True
    plan_rejected = plan_exists and state.recovery_plan.is_approved is False
    action_executed = plan_exists and state.recovery_plan.executed
    verified_pass = state.verification_result is not None and state.verification_result.verified
    verified_fail = state.verification_result is not None and not state.verification_result.verified

    # 1. Incident Detected
    s1 = TrackerStageEvent(
        stage_id=1,
        stage_key="incident_detected",
        stage_name="Incident Detected & Telemetry Ingested",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary="High-volume HTTP 504 Gateway Timeouts detected on student portal ingress endpoint.",
        details={"incident_id": str(incident_id), "priority": "critical", "source": "prometheus-alert"},
        evidence_ids=[uuid.UUID("a1111111-0000-0000-0000-000000000004")],
    )

    # 2. Evidence Correlated
    s2 = TrackerStageEvent(
        stage_id=2,
        stage_key="evidence_correlated",
        stage_name="Multi-Source Evidence Correlation",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary="11 multi-source evidence artifacts normalized across metrics, logs, traces, and helpdesk tickets.",
        details={"total_evidence": 11, "source_types": 9},
        evidence_ids=[
            uuid.UUID("a1111111-0000-0000-0000-000000000001"),
            uuid.UUID("a1111111-0000-0000-0000-000000000003"),
            uuid.UUID("a1111111-0000-0000-0000-000000000005"),
        ],
    )

    # 3. Device & Service Mapped
    s3 = TrackerStageEvent(
        stage_id=3,
        stage_key="device_service_mapped",
        stage_name="Topology & Network Device Mapping",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary="Physical network switch [switch-core-bldg-a] and border gateway mapped to downstream student portal services.",
        details={"mapped_nodes": 6, "edges": 5, "devices": ["switch-core-bldg-a", "gw-border-01"]},
        evidence_ids=[uuid.UUID("a1111111-0000-0000-0000-000000000004")],
    )

    # 4. Hypothesis Generation
    s4 = TrackerStageEvent(
        stage_id=4,
        stage_key="hypothesis_generation",
        stage_name="Competing Failure Hypotheses Generated",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary=f"Formulated {len(state.hypotheses)} competing hypotheses (Network Backbone, Database Pool, Canary Crypto).",
        details={"hypotheses_count": len(state.hypotheses), "leading": state.leading_hypothesis_id},
        evidence_ids=[uuid.UUID("a1111111-0000-0000-0000-000000000002")],
    )

    # 5. Network-First Diagnostics
    s5_status = TrackerStageStatus.COMPLETED if has_network_diagnostic else (
        TrackerStageStatus.IN_PROGRESS if state.current_round == 1 and state.current_stage != InvestigationStage.RESOLVED else TrackerStageStatus.PENDING
    )
    net_tool = next((t for t in state.tool_history if t.category == "network"), None)
    s5 = TrackerStageEvent(
        stage_id=5,
        stage_key="network_diagnostics",
        stage_name="Network-First Diagnostics (L3/L4, DNS, DHCP)",
        category="diagnostics",
        status=s5_status,
        timestamp=net_tool.executed_at if net_tool else None,
        summary=(
            "Network Diagnostic: 0% packet loss, 1.2ms latency, DNS resolved in 3.8ms, core switch 0 errors. "
            "Ruled out campus network outage; isolated failure to upstream auth-service."
            if has_network_diagnostic
            else "Awaiting primary network connectivity and infrastructure health diagnostic."
        ),
        details=net_tool.simulated_output if net_tool else {},
        tool_name="network_connectivity_diagnostic",
    )

    # 6. Supporting Diagnostics
    s6_status = TrackerStageStatus.COMPLETED if has_supporting_diagnostic else (
        TrackerStageStatus.IN_PROGRESS if state.current_round >= 2 and state.current_stage not in (InvestigationStage.RESOLVED, InvestigationStage.REPLANNING) else TrackerStageStatus.PENDING
    )
    db_tool = next((t for t in state.tool_history if t.category in ("database", "deployment_config")), None)
    s6 = TrackerStageEvent(
        stage_id=6,
        stage_key="supporting_investigation",
        stage_name="Supporting Diagnostics (Database & Config Audit)",
        category="diagnostics",
        status=s6_status,
        timestamp=db_tool.executed_at if db_tool else None,
        summary=(
            "Database & Config Diagnostic: 15/15 pool capacity saturated; GitOps commit a8f912c confirmed reducing pool size from 50 to 15."
            if has_supporting_diagnostic
            else "Awaiting branch diagnostics on database connection pool and deployment history."
        ),
        details=db_tool.simulated_output if db_tool else {},
        tool_name="database_diagnostics",
    )

    # 7. Root-Cause Determination
    s7_status = TrackerStageStatus.COMPLETED if leading_conf >= 0.85 else TrackerStageStatus.IN_PROGRESS
    s7 = TrackerStageEvent(
        stage_id=7,
        stage_key="root_cause_assessed",
        stage_name="Root-Cause Determination with Traceable Evidence",
        category="investigation",
        status=s7_status,
        timestamp=now_utc if s7_status == TrackerStageStatus.COMPLETED else None,
        summary=(
            f"Root cause confirmed: {state.leading_hypothesis_id} at {int(leading_conf * 100)}% confidence. "
            "QueuePool limit reduction under peak course registration caused connection starvation."
        ),
        details={"leading_hypothesis": state.leading_hypothesis_id, "confidence": leading_conf},
        evidence_ids=[uuid.UUID("a1111111-0000-0000-0000-000000000001"), uuid.UUID("a1111111-0000-0000-0000-000000000003")],
    )

    # 8. Impact Assessment
    s8_status = TrackerStageStatus.COMPLETED if leading_conf >= 0.85 else TrackerStageStatus.PENDING
    s8 = TrackerStageEvent(
        stage_id=8,
        stage_key="impact_assessed",
        stage_name="Downstream Service & Device Impact Assessment",
        category="investigation",
        status=s8_status,
        timestamp=now_utc if s8_status == TrackerStageStatus.COMPLETED else None,
        summary="Service impact: student-portal-ui (84.2% failure rate), portal-gateway (10.8s P99 latency), and auth-service.",
        details={"impacted_services": ["student-portal-ui", "portal-gateway", "auth-service", "campusops-db"]},
    )

    # 9. Recovery Plan Formulation
    s9_status = TrackerStageStatus.COMPLETED if plan_exists else TrackerStageStatus.PENDING
    s9 = TrackerStageEvent(
        stage_id=9,
        stage_key="recovery_plan_generated",
        stage_name="Safe Non-Destructive Recovery Plan Formulation",
        category="recovery",
        status=s9_status,
        timestamp=now_utc if plan_exists else None,
        summary=(
            f"Formulated Plan: {state.recovery_plan.action_name} (Risk: {state.recovery_plan.risk_level.value.upper()})."
            if plan_exists
            else "Awaiting root-cause determination before recovery plan generation."
        ),
        details={"action": state.recovery_plan.action_name, "risk": state.recovery_plan.risk_level.value} if plan_exists else {},
    )

    # 10. Human Approval Barrier
    if plan_approved:
        s10_status = TrackerStageStatus.COMPLETED
        s10_summary = f"Human operator approved action: {state.recovery_plan.approved_by} at {state.recovery_plan.approved_at}."
    elif plan_rejected:
        s10_status = TrackerStageStatus.REPLANNING
        s10_summary = "Recovery action rejected by human operator. Replanning cycle engaged."
    elif state.current_stage == InvestigationStage.AWAITING_APPROVAL:
        s10_status = TrackerStageStatus.BLOCKED
        s10_summary = "AUTOMATION BLOCKED: Explicit human approval required before remediation can proceed."
    else:
        s10_status = TrackerStageStatus.PENDING
        s10_summary = "Pending recovery plan approval."

    s10 = TrackerStageEvent(
        stage_id=10,
        stage_key="waiting_human_approval",
        stage_name="Human-in-the-Loop Operator Approval Barrier",
        category="recovery",
        status=s10_status,
        timestamp=state.recovery_plan.approved_at if plan_approved else None,
        summary=s10_summary,
        details={"is_approved": state.recovery_plan.is_approved} if plan_exists else {},
    )

    # 11. Simulated Recovery Execution
    s11_status = TrackerStageStatus.COMPLETED if action_executed else (
        TrackerStageStatus.IN_PROGRESS if state.current_stage == InvestigationStage.RECOVERY_EXECUTION else TrackerStageStatus.PENDING
    )
    s11 = TrackerStageEvent(
        stage_id=11,
        stage_key="simulated_recovery_executed",
        stage_name="Simulated Remediation Execution",
        category="recovery",
        status=s11_status,
        timestamp=now_utc if action_executed else None,
        summary=(
            "Applied GitOps values.yaml rollback (database.pool_size = 50) and graceful rolling restart of auth-service."
            if action_executed
            else "Awaiting human authorization and execution trigger."
        ),
        details={"executed": action_executed, "simulated": True},
    )

    # 12. Post-Recovery Telemetry Verification
    if verified_pass:
        s12_status = TrackerStageStatus.COMPLETED
        s12_summary = "Telemetry Verification: All 4 SLA compliance criteria satisfied (P99: 240ms, 504 rate: 0.02%, DB pool: 28%)."
    elif verified_fail:
        s12_status = TrackerStageStatus.REPLANNING
        s12_summary = "Telemetry Verification FAILED: Error rate remains above threshold. Replanning cycle triggered."
    elif state.current_stage in (InvestigationStage.RECOVERY_EXECUTION, InvestigationStage.VERIFICATION):
        s12_status = TrackerStageStatus.IN_PROGRESS
        s12_summary = "Collecting fresh simulated telemetry across 4 SLA compliance dimensions."
    else:
        s12_status = TrackerStageStatus.PENDING
        s12_summary = "Awaiting post-remediation telemetry collection."

    s12 = TrackerStageEvent(
        stage_id=12,
        stage_key="telemetry_verified",
        stage_name="Post-Recovery Telemetry & SLA Verification",
        category="verification",
        status=s12_status,
        timestamp=state.verification_result.completed_at if state.verification_result else None,
        summary=s12_summary,
        details=state.verification_result.post_recovery_metrics if state.verification_result else {},
    )

    # 13. Resolved or Replanning
    if state.current_stage == InvestigationStage.RESOLVED:
        s13_status = TrackerStageStatus.COMPLETED
        s13_summary = "Incident successfully resolved and closed. Remediation verified against live telemetry baseline."
    elif state.current_stage == InvestigationStage.REPLANNING:
        s13_status = TrackerStageStatus.REPLANNING
        s13_summary = "Replanning cycle active: re-evaluating alternative hypotheses and diagnostic paths."
    else:
        s13_status = TrackerStageStatus.PENDING
        s13_summary = "Awaiting verification closure."

    s13 = TrackerStageEvent(
        stage_id=13,
        stage_key="incident_resolved_or_replan",
        stage_name="Incident Resolution OR Replanning Cycle",
        category="verification",
        status=s13_status,
        timestamp=incident.resolved_at if incident and incident.resolved_at else (now_utc if s13_status == TrackerStageStatus.COMPLETED else None),
        summary=s13_summary,
        details={"final_status": incident.status.value if incident else "investigating"},
    )

    stages = [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s12, s13]

    # Compute current active stage ID
    active_stage_id = 1
    for s in stages:
        if s.status in (TrackerStageStatus.IN_PROGRESS, TrackerStageStatus.BLOCKED, TrackerStageStatus.REPLANNING):
            active_stage_id = s.stage_id
            break
        elif s.status == TrackerStageStatus.COMPLETED:
            active_stage_id = min(s.stage_id + 1, 13)

    if state.current_stage == InvestigationStage.RESOLVED:
        active_stage_id = 13

    # Canonical hardware device impact mappings
    device_mapping = [
        HardwareDeviceImpact(
            device_name="switch-core-bldg-a",
            device_type="switch",
            ip_address="10.0.0.1",
            location="Building A Core Rack 1",
            status="ONLINE",
            health_summary={
                "crc_errors": 0,
                "packet_loss_pct": 0.0,
                "optical_tx_rx_dbm": -2.4,
                "fans": "ALL_OK",
                "temp_c": 36.4,
            },
            impacted_services=["portal-gateway", "auth-service", "student-portal-ui"],
            technician_recommendation="Hardware layer is 100% operational. Physical inspection or hardware replacement NOT needed.",
            simulated=True,
        ),
        HardwareDeviceImpact(
            device_name="gw-border-01",
            device_type="router",
            ip_address="10.244.0.1",
            location="Datacenter Edge Ingress",
            status="ONLINE",
            health_summary={
                "throughput_gbps": 8.4,
                "packet_drop_rate": 0.0,
                "tls_handshake_ms": 4.1,
            },
            impacted_services=["portal-gateway", "student-portal-ui"],
            technician_recommendation="Edge routing and TLS certificates valid. Physical inspection NOT required.",
            simulated=True,
        ),
        HardwareDeviceImpact(
            device_name="dns-campus-primary",
            device_type="server",
            ip_address="10.0.0.2",
            location="Campus Core Server Room",
            status="ONLINE",
            health_summary={
                "queries_per_sec": 1240,
                "avg_response_ms": 3.8,
                "authoritative_zone": "campusops.edu",
            },
            impacted_services=["portal-gateway"],
            technician_recommendation="DNS resolution latency 3.8ms within baseline. No hardware maintenance required.",
            simulated=True,
        ),
    ]

    summary_counts = {
        "completed": sum(1 for s in stages if s.status == TrackerStageStatus.COMPLETED),
        "in_progress": sum(1 for s in stages if s.status == TrackerStageStatus.IN_PROGRESS),
        "blocked": sum(1 for s in stages if s.status == TrackerStageStatus.BLOCKED),
        "replanning": sum(1 for s in stages if s.status == TrackerStageStatus.REPLANNING),
        "pending": sum(1 for s in stages if s.status == TrackerStageStatus.PENDING),
    }

    return InvestigationTrackerResponse(
        incident_id=incident_id,
        current_stage_id=active_stage_id,
        current_stage_name=stages[active_stage_id - 1].stage_name,
        overall_status=state.current_stage.value,
        iteration_round=state.current_round,
        elapsed_seconds=elapsed_seconds,
        stages=stages,
        device_mapping=device_mapping,
        summary_counts=summary_counts,
        simulated=True,
    )


