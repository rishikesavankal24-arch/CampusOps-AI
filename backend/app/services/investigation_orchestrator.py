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
from app.services.incident_service import (
    DEMO_INCIDENT_ID,
    SCENARIO_1_ID,
    SCENARIO_2_ID,
    SCENARIO_3_ID,
)


def _build_initial_hypotheses(incident_id: uuid.UUID) -> list[Hypothesis]:
    """Generate canonical 3 competing hypotheses with supporting evidence references."""
    if incident_id == SCENARIO_2_ID:
        return [
            Hypothesis(
                id="HYP-01",
                title="Campus Wi-Fi Ingress & Core DHCP Scope Exhaustion",
                explanation=(
                    "Access point ap-lib-floor2 experiencing severe RF channel saturation and client association overload. "
                    "Core DHCP pool 10.0.4.0/24 has 0 available leases, rejecting mobile devices and causing APIPA fallback."
                ),
                category="network",
                supporting_evidence_ids=[
                    uuid.UUID("b2222222-0000-0000-0000-000000000001"),
                    uuid.UUID("b2222222-0000-0000-0000-000000000002"),
                    uuid.UUID("b2222222-0000-0000-0000-000000000003"),
                    uuid.UUID("b2222222-0000-0000-0000-000000000004"),
                    uuid.UUID("b2222222-0000-0000-0000-000000000005"),
                ],
                contradicting_evidence_ids=[],
                confidence_score=0.85,
                confidence_rationale="Infoblox IPAM confirms 254/254 leases allocated and AP telemetry shows 94.2% RF channel saturation.",
                status=HypothesisStatus.OPEN,
                suspected_components=["ap-lib-floor2", "gw-border-01"],
            ),
            Hypothesis(
                id="HYP-02",
                title="Core Backbone Switch VLAN Tagging / Spanning Tree Loop",
                explanation=(
                    "Spanning Tree Protocol (STP) topology change or VLAN 104 trunk negotiation failure between "
                    "switch-core-bldg-a and the border router causing broadcast packet storms."
                ),
                category="network",
                supporting_evidence_ids=[
                    uuid.UUID("b2222222-0000-0000-0000-000000000004"),
                ],
                contradicting_evidence_ids=[],
                confidence_score=0.35,
                confidence_rationale="Core switch port GigabitEthernet 1/0/14 reported 2.4% CRC drops during morning traffic peak.",
                status=HypothesisStatus.OPEN,
                suspected_components=["switch-core-bldg-a"],
            ),
            Hypothesis(
                id="HYP-03",
                title="Database Connection Pool Starvation on Student Portal",
                explanation=(
                    "Backend database unable to service client requests, manifesting as student connection dropouts."
                ),
                category="database",
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[
                    uuid.UUID("b2222222-0000-0000-0000-000000000003"),
                ],
                confidence_score=0.15,
                confidence_rationale="Client error logs show APIPA self-assigned IP (169.254.x.x); failure happens before L7 reachability.",
                status=HypothesisStatus.OPEN,
                suspected_components=["campusops-db"],
            ),
        ]

    elif incident_id == SCENARIO_3_ID:
        return [
            Hypothesis(
                id="HYP-01",
                title="Campus Ingress Network / Border Gateway Latency Degradation",
                explanation=(
                    "Border gateway experiencing packet drop or upstream connection degradation on student login traffic."
                ),
                category="network",
                supporting_evidence_ids=[
                    uuid.UUID("c3333333-0000-0000-0000-000000000005"),
                ],
                contradicting_evidence_ids=[],
                confidence_score=0.20,
                confidence_rationale="Gateway reports 504 timeouts, but network interface throughput remains within nominal limits.",
                status=HypothesisStatus.OPEN,
                suspected_components=["portal-gateway"],
            ),
            Hypothesis(
                id="HYP-02",
                title="PostgreSQL Core Database Connection Pool Saturation",
                explanation=(
                    "Database connection queue saturation causing queries to block and auth-service to time out."
                ),
                category="database",
                supporting_evidence_ids=[],
                contradicting_evidence_ids=[
                    uuid.UUID("c3333333-0000-0000-0000-000000000004"),
                ],
                confidence_score=0.30,
                confidence_rationale="Trace spans show auth:db_pool_acquisition took only 14ms; database is not the bottleneck.",
                status=HypothesisStatus.OPEN,
                suspected_components=["campusops-db"],
            ),
            Hypothesis(
                id="HYP-03",
                title="Auth-Service v2.4.1 Canary Argon2id Crypto Thread Saturation",
                explanation=(
                    "Canary rollout of auth-service:v2.4.1 increased Argon2id memory cost parameter to 64MB (65536 KB). "
                    "Concurrency bursts saturate CPU worker threads and cause 42.1% CFS throttling, tripping 10s gateway timeouts."
                ),
                category="software",
                supporting_evidence_ids=[
                    uuid.UUID("c3333333-0000-0000-0000-000000000001"),
                    uuid.UUID("c3333333-0000-0000-0000-000000000002"),
                    uuid.UUID("c3333333-0000-0000-0000-000000000003"),
                    uuid.UUID("c3333333-0000-0000-0000-000000000004"),
                    uuid.UUID("c3333333-0000-0000-0000-000000000005"),
                ],
                contradicting_evidence_ids=[],
                confidence_score=0.85,
                confidence_rationale="OpenTelemetry trace isolates 8,240ms delay inside auth:argon2_verify span; cgroup CPU is 98.4% pegged.",
                status=HypothesisStatus.OPEN,
                suspected_components=["auth-service", "portal-gateway"],
            ),
        ]

    # Scenario 1 (Default)
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

    leading_id = "HYP-01" if incident_id == SCENARIO_2_ID else ("HYP-03" if incident_id == SCENARIO_3_ID else "HYP-02")
    classification = IncidentClassification.HARDWARE if incident_id == SCENARIO_2_ID else IncidentClassification.SOFTWARE

    state = InvestigationStateResponse(
        incident_id=incident_id,
        current_stage=InvestigationStage.HYPOTHESIS_GENERATION,
        current_round=1,
        max_rounds=3,
        classification=classification,
        hypotheses=hypotheses,
        leading_hypothesis_id=leading_id,
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
            tool_name = "deployment_config_diagnostics" if incident_id == SCENARIO_3_ID else "database_diagnostics"
        else:
            tool_name = "deployment_config_diagnostics"

    now_iso = datetime.now(timezone.utc).isoformat()

    # Scenario 2 Branch: Physical Campus Wi-Fi & DHCP Pool Exhaustion
    if incident_id == SCENARIO_2_ID:
        if tool_name == "network_connectivity_diagnostic":
            tool_call = diagnostic_tools.run_network_connectivity_diagnostic(
                target_service=target_service or "ap-lib-floor2",
                round_num=state.current_round,
                incident_id=incident_id,
            )
            for h in state.hypotheses:
                if h.id == "HYP-01":
                    h.confidence_score = 0.96
                    h.status = HypothesisStatus.SUPPORTED
                    h.confidence_rationale = (
                        "DIAGNOSTIC CONFIRMED: 24.8% packet loss on ap-lib-floor2 with 94.2% RF channel saturation. "
                        "DHCP scope 10.0.4.0/24 has 0 available leases (100% capacity), rejecting client associations."
                    )
                elif h.id == "HYP-02":
                    h.confidence_score = 0.15
                    h.status = HypothesisStatus.WEAKENED
                    h.confidence_rationale = "Switch port CRC errors are minimal (0.1%); failure is localized to AP and DHCP."
                elif h.id == "HYP-03":
                    h.confidence_score = 0.05
                    h.status = HypothesisStatus.REJECTED
                    h.confidence_rationale = "DB connection pool healthy; problem is L2/L3 wireless and IP address assignment."

            state.classification = IncidentClassification.HARDWARE
            state.audit_log.append({
                "timestamp": now_iso,
                "event": "TOOL_EXECUTED",
                "tool": "network_connectivity_diagnostic",
                "insight": tool_call.interpreted_insight,
                "effect": "Confirmed HYP-01 (Wi-Fi & DHCP Scope Exhaustion) as Root Cause at 0.96 confidence.",
            })

            state.current_stage = InvestigationStage.AWAITING_APPROVAL
            state.leading_hypothesis_id = "HYP-01"
            state.recovery_plan = RecoveryPlan(
                action_id="ACT-DHCP-EXPAND-02",
                action_name="Expand DHCP Subnet Scope to /23 & Rebalance AP RF Channels",
                action_type="network_remediation",
                rationale=(
                    "Expand DHCP wireless scope on VLAN 104 from 10.0.4.0/24 (254 leases) to 10.0.4.0/23 (510 leases), "
                    "flush expired client leases via DHCPRELEASE sweep, and reassign ap-lib-floor2 to 5GHz Channel 149."
                ),
                expected_signal=(
                    "DHCP available leases > 250; Wi-Fi packet loss < 1%; Client association latency < 50ms; "
                    "Student portal login success > 99%."
                ),
                risk_level=RiskLevel.MEDIUM,
                affected_services=["ap-lib-floor2", "gw-border-01", "student-portal-ui"],
                rollback_plan="Restore DHCP scope to /24 via Infoblox API if upstream router ARP table overflows.",
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
            state.tool_history.append(tool_call)

            # Persist
            stmt = select(Incident).where(Incident.id == incident_id)
            res = await db.execute(stmt)
            incident = res.scalars().first()
            if incident:
                incident.ai_root_cause = state.model_dump(mode="json")
                await db.commit()
            return state

    # Scenario 3 Branch: Canary Argon2 CPU Starvation
    elif incident_id == SCENARIO_3_ID:
        if tool_name == "network_connectivity_diagnostic":
            tool_call = diagnostic_tools.run_network_connectivity_diagnostic(
                target_service=target_service or "portal-gateway",
                round_num=state.current_round,
                incident_id=incident_id,
            )
            for h in state.hypotheses:
                if h.id == "HYP-01":
                    h.confidence_score = 0.10
                    h.status = HypothesisStatus.REJECTED
                    h.confidence_rationale = (
                        "DIAGNOSTIC PROVEN FALSE: Campus network and border gateway report 0% packet loss "
                        "and 1.2ms latency. Physical network is fully operational."
                    )
                elif h.id == "HYP-03":
                    h.confidence_score = 0.90
                    h.confidence_rationale = "Network layer ruled out; isolates latency cascade directly to auth-service crypto worker."

            state.classification = IncidentClassification.SOFTWARE
            state.audit_log.append({
                "timestamp": now_iso,
                "event": "TOOL_EXECUTED",
                "tool": "network_connectivity_diagnostic",
                "insight": tool_call.interpreted_insight,
                "effect": "Weakened HYP-01 (Network) to 0.10 (REJECTED); Elevated HYP-03 (Canary Crypto) to 0.90.",
            })
            state.tool_history.append(tool_call)
            state.current_stage = InvestigationStage.CONFIDENCE_UPDATE
            state.current_round = 2

        elif tool_name in ("deployment_config_diagnostics", "application_diagnostics"):
            tool_call = diagnostic_tools.run_deployment_config_diagnostics(
                target_service=target_service or "auth-service",
                round_num=state.current_round,
                incident_id=incident_id,
            )
            for h in state.hypotheses:
                if h.id == "HYP-03":
                    h.confidence_score = 0.98
                    h.status = HypothesisStatus.SUPPORTED
                    h.confidence_rationale = (
                        "ROOT CAUSE CONFIRMED: Canary v2.4.1 (commit d981a2f) quadrupled Argon2id memory_cost "
                        "to 64MB per hash, saturating CPU worker threads at 98.4% and tripping gateway 10s timeouts."
                    )
                elif h.id == "HYP-02":
                    h.confidence_score = 0.10
                    h.status = HypothesisStatus.REJECTED
                    h.confidence_rationale = "DB pool is 100% healthy with 0 queue wait; crypto hashing is the sole bottleneck."

            state.audit_log.append({
                "timestamp": now_iso,
                "event": "TOOL_EXECUTED",
                "tool": tool_name,
                "insight": tool_call.interpreted_insight,
                "effect": "Confirmed HYP-03 as Root Cause at 0.98 confidence.",
            })
            state.tool_history.append(tool_call)

            state.current_stage = InvestigationStage.AWAITING_APPROVAL
            state.leading_hypothesis_id = "HYP-03"
            state.recovery_plan = RecoveryPlan(
                action_id="ACT-ROLLBACK-CANARY-03",
                action_name="ArgoCD Rollback auth-service to Stable v2.4.0",
                action_type="service_rollback",
                rationale=(
                    "Execute automated ArgoCD rollback of auth-service deployment to stable release v2.4.0, "
                    "reverting Argon2id memory_cost to 16MB and eliminating CFS CPU throttling."
                ),
                expected_signal=(
                    "Auth-service CPU utilization drops below 25%; Argon2 hash duration drops to 310ms; "
                    "Gateway 504 error rate drops to < 0.1%."
                ),
                risk_level=RiskLevel.LOW,
                affected_services=["auth-service", "portal-gateway"],
                rollback_plan="Re-apply canary release with 0% weight.",
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

        stmt = select(Incident).where(Incident.id == incident_id)
        res = await db.execute(stmt)
        incident = res.scalars().first()
        if incident:
            incident.ai_root_cause = state.model_dump(mode="json")
            await db.commit()
        return state

    # Scenario 1 (Default Database Connection Pool Starvation)
    if tool_name == "network_connectivity_diagnostic":
        tool_call = diagnostic_tools.run_network_connectivity_diagnostic(
            target_service=target_service or "portal-gateway",
            round_num=state.current_round,
            incident_id=incident_id,
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
            incident_id=incident_id,
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
            incident_id=incident_id,
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
            incident_id=incident_id,
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

    # Determine scenario-specific remediation and metrics
    if incident_id == SCENARIO_2_ID:
        applied_changes = [
            "Infoblox DHCP scope expanded: 10.0.4.0/23 (510 dynamic leases provisioned)",
            "Stale client leases flushed via DHCPRELEASE sweep",
            "Cisco Catalyst AP ap-lib-floor2 reassigned to 5GHz Channel 149 (40MHz width)",
        ]
        pre_metrics = {
            "wifi_packet_loss_pct": 24.8,
            "dhcp_available_leases": 0,
            "ap_channel_utilization_pct": 94.2,
            "portal_login_failure_rate": 0.920,
        }
        post_metrics = {
            "wifi_packet_loss_pct": 0.1,
            "dhcp_available_leases": 256,
            "ap_channel_utilization_pct": 28.4,
            "portal_login_failure_rate": 0.004,
        }
        checks = [
            {"metric": "Wi-Fi Packet Loss", "threshold": "< 1.0%", "value": "0.1%", "passed": True},
            {"metric": "DHCP Available Leases", "threshold": "> 100", "value": "256 available", "passed": True},
            {"metric": "AP RF Channel Saturation", "threshold": "< 50%", "value": "28.4%", "passed": True},
            {"metric": "Student Portal Login Success", "threshold": "> 98.0%", "value": "99.6%", "passed": True},
        ]
        outcome_msg = "VERIFICATION SUCCESS: DHCP scope expanded to /23 (256 leases available) and Wi-Fi packet loss reduced to 0.1%."
    elif incident_id == SCENARIO_3_ID:
        applied_changes = [
            "ArgoCD sync initiated: auth-service rollback to git commit c4118be (v2.4.0)",
            "Argon2id memory_cost reverted to 16384 KB (16 MB) in Helm values.yaml",
            "Graceful pod rolling restart completed (3/3 Ready, 0 restarts)",
        ]
        pre_metrics = {
            "auth_cpu_utilization_pct": 98.4,
            "argon2_verify_duration_ms": 8240,
            "gateway_504_error_rate": 0.412,
            "p99_latency_seconds": 10.12,
        }
        post_metrics = {
            "auth_cpu_utilization_pct": 18.2,
            "argon2_verify_duration_ms": 310,
            "gateway_504_error_rate": 0.0002,
            "p99_latency_seconds": 0.21,
        }
        checks = [
            {"metric": "Auth Pod CPU Utilization", "threshold": "< 40%", "value": "18.2%", "passed": True},
            {"metric": "Argon2 Hash Duration", "threshold": "< 400ms", "value": "310ms", "passed": True},
            {"metric": "Gateway 504 Error Rate", "threshold": "< 0.5%", "value": "0.02%", "passed": True},
            {"metric": "P99 Ingress Latency", "threshold": "< 1.2s", "value": "210ms", "passed": True},
        ]
        outcome_msg = "VERIFICATION SUCCESS: Auth pod CPU drops to 18.2% and Argon2 latency normalized to 310ms."
    else:
        applied_changes = [
            "GitOps commit revert applied (values.yaml: database.pool_size = 50)",
            "Rolling pod restart completed for auth-service (3/3 Ready)",
            "Active idle-in-transaction connection handles released",
        ]
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
        outcome_msg = "VERIFICATION SUCCESS: All SLA criteria satisfied. Incident successfully resolved."

    # 1. Mark simulated recovery action executed
    state.recovery_plan.executed = True
    state.audit_log.append({
        "timestamp": now_iso,
        "event": "SIMULATED_RECOVERY_EXECUTED",
        "action": state.recovery_plan.action_name,
        "applied_changes": applied_changes,
    })

    # 2. Generate simulated verification telemetry
    if force_verification_failure:
        fail_post = dict(pre_metrics)
        fail_checks = [
            {"metric": "Error Rate", "threshold": "< 0.5%", "value": "11.5%", "passed": False},
            {"metric": "P99 Ingress Latency", "threshold": "< 1.2s", "value": "9.42s", "passed": False},
        ]
        verification = VerificationResult(
            verified=False,
            pre_recovery_metrics=pre_metrics,
            post_recovery_metrics=fail_post,
            checks=fail_checks,
            outcome_summary="VERIFICATION FAILED: Metrics remain above SLA threshold. Orchestrator triggered replanning.",
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
        verification = VerificationResult(
            verified=True,
            pre_recovery_metrics=pre_metrics,
            post_recovery_metrics=post_metrics,
            checks=checks,
            outcome_summary=outcome_msg,
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
    if incident_id == SCENARIO_2_ID:
        s1_summary = "Campus Wi-Fi degradation & DHCP starvation reported by mobile clients in Library."
        s1_evidence = [uuid.UUID("b2222222-0000-0000-0000-000000000001")]
        s2_summary = "5 multi-source telemetry items correlated across Cisco AP RF metrics, Infoblox IPAM, and client logs."
        s2_evidence = [uuid.UUID("b2222222-0000-0000-0000-000000000001"), uuid.UUID("b2222222-0000-0000-0000-000000000002")]
        s3_summary = "Access point [ap-lib-floor2] and core DHCP relay mapped to downstream student portal service."
        s3_details = {"mapped_nodes": 4, "edges": 3, "devices": ["ap-lib-floor2", "gw-border-01", "switch-core-bldg-a"]}
    elif incident_id == SCENARIO_3_ID:
        s1_summary = "High-volume HTTP 504 timeouts and auth latency spikes following ArgoCD canary rollout."
        s1_evidence = [uuid.UUID("c3333333-0000-0000-0000-000000000005")]
        s2_summary = "5 multi-source artifacts correlated across Helm release logs, cgroup CPU metrics, and distributed traces."
        s2_evidence = [uuid.UUID("c3333333-0000-0000-0000-000000000001"), uuid.UUID("c3333333-0000-0000-0000-000000000003")]
        s3_summary = "Auth-service container pods mapped to ingress gateway, database, and campus LDAP directory."
        s3_details = {"mapped_nodes": 5, "edges": 4, "devices": ["portal-gateway", "auth-service"]}
    else:
        s1_summary = "High-volume HTTP 504 Gateway Timeouts detected on student portal ingress endpoint."
        s1_evidence = [uuid.UUID("a1111111-0000-0000-0000-000000000004")]
        s2_summary = "11 multi-source evidence artifacts normalized across metrics, logs, traces, and helpdesk tickets."
        s2_evidence = [uuid.UUID("a1111111-0000-0000-0000-000000000001"), uuid.UUID("a1111111-0000-0000-0000-000000000003")]
        s3_summary = "Physical network switch [switch-core-bldg-a] and border gateway mapped to downstream student portal services."
        s3_details = {"mapped_nodes": 6, "edges": 5, "devices": ["switch-core-bldg-a", "gw-border-01"]}

    s1 = TrackerStageEvent(
        stage_id=1,
        stage_key="incident_detected",
        stage_name="Incident Detected & Telemetry Ingested",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary=s1_summary,
        details={"incident_id": str(incident_id), "priority": "critical", "source": "telemetry-stream"},
        evidence_ids=s1_evidence,
    )

    # 2. Evidence Correlated
    s2 = TrackerStageEvent(
        stage_id=2,
        stage_key="evidence_correlated",
        stage_name="Multi-Source Evidence Correlation",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary=s2_summary,
        details={"total_evidence": len(s2_evidence)},
        evidence_ids=s2_evidence,
    )

    # 3. Device & Service Mapped
    s3 = TrackerStageEvent(
        stage_id=3,
        stage_key="device_service_mapped",
        stage_name="Topology & Network Device Mapping",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary=s3_summary,
        details=s3_details,
        evidence_ids=s1_evidence,
    )

    # 4. Hypothesis Generation
    s4 = TrackerStageEvent(
        stage_id=4,
        stage_key="hypothesis_generation",
        stage_name="Competing Failure Hypotheses Generated",
        category="investigation",
        status=TrackerStageStatus.COMPLETED,
        timestamp=created_at,
        summary=f"Formulated {len(state.hypotheses)} competing hypotheses. Leading: {state.leading_hypothesis_id}.",
        details={"hypotheses_count": len(state.hypotheses), "leading": state.leading_hypothesis_id},
        evidence_ids=s1_evidence,
    )

    # 5. Network-First Diagnostics
    s5_status = TrackerStageStatus.COMPLETED if has_network_diagnostic else (
        TrackerStageStatus.IN_PROGRESS if state.current_round == 1 and state.current_stage != InvestigationStage.RESOLVED else TrackerStageStatus.PENDING
    )
    net_tool = next((t for t in state.tool_history if t.category == "network"), None)
    if has_network_diagnostic:
        if incident_id == SCENARIO_2_ID:
            s5_summary = "Network Diagnostic CONFIRMED: 24.8% packet loss on ap-lib-floor2 with 94.2% RF saturation. DHCP scope 10.0.4.0/24 exhausted (0 available leases)."
        else:
            s5_summary = "Network Diagnostic: 0% packet loss, 1.2ms latency, DNS resolved in 3.8ms, core switch 0 errors. Ruled out campus network outage; isolated failure to upstream service."
    else:
        s5_summary = "Awaiting primary network connectivity and infrastructure health diagnostic."

    s5 = TrackerStageEvent(
        stage_id=5,
        stage_key="network_diagnostics",
        stage_name="Network-First Diagnostics (L3/L4, DNS, DHCP)",
        category="diagnostics",
        status=s5_status,
        timestamp=net_tool.executed_at if net_tool else None,
        summary=s5_summary,
        details=net_tool.simulated_output if net_tool else {},
        tool_name="network_connectivity_diagnostic",
    )

    # 6. Supporting Diagnostics
    s6_status = TrackerStageStatus.COMPLETED if has_supporting_diagnostic else (
        TrackerStageStatus.IN_PROGRESS if state.current_round >= 2 and state.current_stage not in (InvestigationStage.RESOLVED, InvestigationStage.REPLANNING) else TrackerStageStatus.PENDING
    )
    db_tool = next((t for t in state.tool_history if t.category in ("database", "deployment_config")), None)
    if has_supporting_diagnostic:
        if incident_id == SCENARIO_3_ID:
            s6_summary = "Configuration Audit: GitOps commit d981a2f quadrupled Argon2id memory_cost to 64MB; CPU throttled at 98.4%."
        else:
            s6_summary = "Database & Config Diagnostic: 15/15 pool capacity saturated; GitOps commit a8f912c confirmed reducing pool size from 50 to 15."
    else:
        s6_summary = "Awaiting branch diagnostics on application runtime and configuration audit."

    s6 = TrackerStageEvent(
        stage_id=6,
        stage_key="supporting_investigation",
        stage_name="Supporting Diagnostics (Database & Config Audit)",
        category="diagnostics",
        status=s6_status,
        timestamp=db_tool.executed_at if db_tool else None,
        summary=s6_summary,
        details=db_tool.simulated_output if db_tool else {},
        tool_name="deployment_config_diagnostics" if incident_id == SCENARIO_3_ID else "database_diagnostics",
    )

    # 7. Root-Cause Determination
    s7_status = TrackerStageStatus.COMPLETED if leading_conf >= 0.85 else TrackerStageStatus.IN_PROGRESS
    if incident_id == SCENARIO_2_ID:
        s7_summary = f"Root cause confirmed: {state.leading_hypothesis_id} at {int(leading_conf * 100)}% confidence. AP client overload and DHCP pool exhaustion."
    elif incident_id == SCENARIO_3_ID:
        s7_summary = f"Root cause confirmed: {state.leading_hypothesis_id} at {int(leading_conf * 100)}% confidence. Canary Argon2 memory cost increase caused 98.4% CPU thrashing."
    else:
        s7_summary = f"Root cause confirmed: {state.leading_hypothesis_id} at {int(leading_conf * 100)}% confidence. QueuePool limit reduction caused connection starvation."

    s7 = TrackerStageEvent(
        stage_id=7,
        stage_key="root_cause_assessed",
        stage_name="Root-Cause Determination with Traceable Evidence",
        category="investigation",
        status=s7_status,
        timestamp=now_utc if s7_status == TrackerStageStatus.COMPLETED else None,
        summary=s7_summary,
        details={"leading_hypothesis": state.leading_hypothesis_id, "confidence": leading_conf},
        evidence_ids=s2_evidence,
    )

    # 8. Impact Assessment
    s8_status = TrackerStageStatus.COMPLETED if leading_conf >= 0.85 else TrackerStageStatus.PENDING
    if incident_id == SCENARIO_2_ID:
        s8_summary = "Service impact: student-portal-ui (92.0% failure rate for wireless clients), ap-lib-floor2 (128 associations), gw-border-01 (42 rejected discovers)."
        s8_services = ["student-portal-ui", "ap-lib-floor2", "gw-border-01"]
    elif incident_id == SCENARIO_3_ID:
        s8_summary = "Service impact: student-portal-ui (41.2% login failure rate), portal-gateway (10.1s P99 latency), auth-service (98.4% CPU saturation)."
        s8_services = ["student-portal-ui", "portal-gateway", "auth-service"]
    else:
        s8_summary = "Service impact: student-portal-ui (84.2% failure rate), portal-gateway (10.8s P99 latency), and auth-service."
        s8_services = ["student-portal-ui", "portal-gateway", "auth-service", "campusops-db"]

    s8 = TrackerStageEvent(
        stage_id=8,
        stage_key="impact_assessed",
        stage_name="Downstream Service & Device Impact Assessment",
        category="investigation",
        status=s8_status,
        timestamp=now_utc if s8_status == TrackerStageStatus.COMPLETED else None,
        summary=s8_summary,
        details={"impacted_services": s8_services},
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
    if incident_id == SCENARIO_2_ID:
        device_mapping = [
            HardwareDeviceImpact(
                device_name="ap-lib-floor2",
                device_type="access_point",
                ip_address="10.244.12.5",
                location="Library Floor 2 Common Area",
                status="DEGRADED (HIGH PACKET LOSS)",
                health_summary={
                    "packet_loss_pct": 24.8,
                    "active_clients": 128,
                    "channel_utilization_pct": 94.2,
                    "rf_band": "5GHz (Channel 36)",
                    "snr_db": 12.4,
                },
                impacted_services=["student-portal-ui", "ap-lib-floor2"],
                technician_recommendation="Access point is oversubscribed with 128 clients. Recommend dynamic RF channel rebalance to Channel 149 and DHCP lease expansion.",
                simulated=True,
            ),
            HardwareDeviceImpact(
                device_name="gw-border-01",
                device_type="router",
                ip_address="10.244.0.1",
                location="Datacenter Edge Ingress",
                status="DEGRADED (DHCP EXHAUSTION)",
                health_summary={
                    "dhcp_scope": "10.0.4.0/24",
                    "active_leases": 254,
                    "available_leases": 0,
                    "dropped_discovers": 42,
                },
                impacted_services=["portal-gateway", "student-portal-ui"],
                technician_recommendation="DHCP pool reached 100% capacity. Expand subnet scope from /24 to /23 to support additional 256 mobile student clients.",
                simulated=True,
            ),
            HardwareDeviceImpact(
                device_name="switch-core-bldg-a",
                device_type="switch",
                ip_address="10.0.0.1",
                location="Building A Core Rack 1",
                status="ONLINE",
                health_summary={
                    "crc_errors": 0,
                    "packet_loss_pct": 0.0,
                    "link_state": "10G Full-Duplex",
                    "fans": "ALL_OK",
                },
                impacted_services=["ap-lib-floor2"],
                technician_recommendation="Core L2/L3 switch healthy. Hardware replacement NOT required.",
                simulated=True,
            ),
        ]
    else:
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


