"""Automated test suite for VeriOps Phase 2: Network-First Investigation Agent.

Verifies:
- Multi-hypothesis generation with explicit supporting evidence links.
- Network-first diagnostic tool execution policy.
- Diagnostic results weakening/rejecting network hypothesis and branching to backend.
- Confidence scoring updates across diagnostic iterations.
- Mandatory human approval barrier before simulated recovery execution.
- Successful post-recovery verification loop resolving the incident.
- Failed verification triggering replanning cycle.
- Audit trail logging and SIMULATED labels.
- Security enforcement (401/403) and 404 handling.
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.auth_service import create_access_token
from app.services.incident_service import DEMO_INCIDENT_ID


@pytest.fixture
async def sre_user(db_session: AsyncSession) -> tuple[User, str]:
    """Create an active SRE support user and return (user, access_token)."""
    user = User(
        email="sre_investigator_p2@campus.edu",
        name="Phase 2 Investigator",
        role=UserRole.SUPPORT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token, _ = create_access_token(user.id, user.email, user.role)
    return user, token


@pytest.mark.asyncio
async def test_investigation_auth_and_not_found(
    client: AsyncClient, sre_user: tuple[User, str]
):
    """Ensure all investigation endpoints enforce authentication and handle 404s."""
    # Unauthenticated
    endpoints = [
        ("GET", f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation"),
        ("POST", f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose"),
        ("POST", f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/approve"),
        ("POST", f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/execute-recovery"),
    ]
    for method, path in endpoints:
        if method == "POST":
            res = await client.post(path, json={})
        else:
            res = await client.get(path)
        assert res.status_code in (401, 403)

    # 404 for unknown incident with authenticated user
    _, token = sre_user
    headers = {"Authorization": f"Bearer {token}"}
    random_id = uuid.uuid4()

    res_404 = await client.get(f"/api/v1/incidents/{random_id}/investigation", headers=headers)
    assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_investigation_lifecycle_network_first_to_resolution(
    client: AsyncClient, sre_user: tuple[User, str]
):
    """Test complete end-to-end investigation lifecycle from network-first diagnostic to verified resolution."""
    _, token = sre_user
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Seed Demo Incident first
    seed_res = await client.post("/api/v1/incidents/seed-demo", headers=headers)
    assert seed_res.status_code == 201

    # 2. Initialize / Read Investigation State
    init_res = await client.get(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation", headers=headers
    )
    assert init_res.status_code == 200
    state = init_res.json()

    assert state["incident_id"] == str(DEMO_INCIDENT_ID)
    assert len(state["hypotheses"]) >= 3
    hyp_ids = [h["id"] for h in state["hypotheses"]]
    assert "HYP-01" in hyp_ids  # Network
    assert "HYP-02" in hyp_ids  # DB Pool Starvation
    assert "HYP-03" in hyp_ids  # Canary Crypto

    # Verify all hypotheses have supporting evidence references
    for h in state["hypotheses"]:
        assert len(h["supporting_evidence_ids"]) > 0
        assert 0.0 <= h["confidence_score"] <= 1.0

    # 3. Round 1: Network-First Diagnostic Execution
    # By default, orchestrator executes network_connectivity_diagnostic in round 1
    diag1_res = await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose",
        headers=headers,
        json={},
    )
    assert diag1_res.status_code == 200
    diag1_state = diag1_res.json()

    assert len(diag1_state["tool_history"]) == 1
    tool1 = diag1_state["tool_history"][0]
    assert tool1["tool_name"] == "network_connectivity_diagnostic"
    assert tool1["category"] == "network"
    assert tool1["simulated"] is True
    assert tool1["simulated_output"]["icmp_ping"]["packet_loss_pct"] == 0.0

    # Verify Network Diagnostic weakened HYP-01 and elevated HYP-02
    hyp_map = {h["id"]: h for h in diag1_state["hypotheses"]}
    assert hyp_map["HYP-01"]["status"] == "rejected"
    assert hyp_map["HYP-01"]["confidence_score"] <= 0.15
    assert hyp_map["HYP-02"]["confidence_score"] >= 0.85

    # 4. Round 2: Branch to Database Diagnostic
    diag2_res = await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose",
        headers=headers,
        json={"tool_name": "database_diagnostics"},
    )
    assert diag2_res.status_code == 200
    diag2_state = diag2_res.json()

    assert len(diag2_state["tool_history"]) == 2
    tool2 = diag2_state["tool_history"][1]
    assert tool2["tool_name"] == "database_diagnostics"
    assert tool2["simulated_output"]["connection_pool"]["utilization_pct"] == 100.0

    # Verify Recovery Plan Formulated and Awaiting Approval
    assert diag2_state["current_stage"] == "AWAITING_APPROVAL"
    assert diag2_state["recovery_plan"] is not None
    plan = diag2_state["recovery_plan"]
    assert plan["action_type"] == "config_revert"
    assert plan["requires_human_approval"] is True
    assert plan["is_approved"] is None

    # 5. Security Barrier Check: Cannot execute recovery without approval!
    exec_blocked = await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/execute-recovery",
        headers=headers,
        json={},
    )
    assert exec_blocked.status_code == 403
    assert "SAFETY VIOLATION" in exec_blocked.json()["detail"]

    # 6. Human Approval Step
    approve_res = await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/approve",
        headers=headers,
        json={"decision": "approve", "notes": "Approved by Lead SRE for simulated deployment."},
    )
    assert approve_res.status_code == 200
    approved_state = approve_res.json()
    assert approved_state["current_stage"] == "RECOVERY_EXECUTION"
    assert approved_state["recovery_plan"]["is_approved"] is True

    # 7. Execute Recovery and Run Verification
    exec_res = await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/execute-recovery",
        headers=headers,
        json={"force_verification_failure": False},
    )
    assert exec_res.status_code == 200
    resolved_state = exec_res.json()

    assert resolved_state["current_stage"] == "RESOLVED"
    assert resolved_state["verification_result"] is not None
    verification = resolved_state["verification_result"]
    assert verification["verified"] is True
    assert all(c["passed"] for c in verification["checks"])
    assert verification["post_recovery_metrics"]["gateway_504_error_rate"] < 0.001
    assert verification["post_recovery_metrics"]["gateway_p99_latency_seconds"] < 0.50

    # 8. Verify Incident model updated to RESOLVED in database
    inc_res = await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}", headers=headers)
    assert inc_res.status_code == 200
    assert inc_res.json()["status"] == "resolved"


@pytest.mark.asyncio
async def test_investigation_failed_verification_triggers_replanning(
    client: AsyncClient, sre_user: tuple[User, str]
):
    """Test that failed verification forces orchestrator back into REPLANNING state."""
    _, token = sre_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    # Fast forward through diagnostic and approval
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose",
        headers=headers,
        json={"tool_name": "network_connectivity_diagnostic"},
    )
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose",
        headers=headers,
        json={"tool_name": "database_diagnostics"},
    )
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/approve",
        headers=headers,
        json={"decision": "approve"},
    )

    # Execute with forced verification failure
    exec_fail_res = await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/execute-recovery",
        headers=headers,
        json={"force_verification_failure": True},
    )
    assert exec_fail_res.status_code == 200
    replan_state = exec_fail_res.json()

    # Must be in REPLANNING, NOT RESOLVED!
    assert replan_state["current_stage"] == "REPLANNING"
    assert replan_state["verification_result"]["verified"] is False

    # Check incident was NOT marked resolved
    inc_res = await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}", headers=headers)
    assert inc_res.json()["status"] != "resolved"


@pytest.mark.asyncio
async def test_investigation_reset(client: AsyncClient, sre_user: tuple[User, str]):
    """Ensure investigation can be reset for repeated live demonstrations."""
    _, token = sre_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose",
        headers=headers,
        json={},
    )

    reset_res = await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/reset",
        headers=headers,
    )
    assert reset_res.status_code == 200
    data = reset_res.json()
    assert data["current_stage"] == "HYPOTHESIS_GENERATION"
    assert len(data["tool_history"]) == 0


@pytest.mark.asyncio
async def test_investigation_tracker_stages_and_device_mapping(
    client: AsyncClient, sre_user: tuple[User, str]
):
    """Verify persistent tracker maintains 13 canonical stages and maps network devices to services."""
    _, token = sre_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    res = await client.get(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/tracker",
        headers=headers,
    )
    assert res.status_code == 200
    tracker = res.json()

    assert tracker["incident_id"] == str(DEMO_INCIDENT_ID)
    assert len(tracker["stages"]) == 13

    # Verify stage ordering 1..13
    for idx, s in enumerate(tracker["stages"], start=1):
        assert s["stage_id"] == idx

    # Verify device mapping
    assert len(tracker["device_mapping"]) >= 2
    device_names = [d["device_name"] for d in tracker["device_mapping"]]
    assert "switch-core-bldg-a" in device_names
    assert "gw-border-01" in device_names

    switch_dev = next(d for d in tracker["device_mapping"] if d["device_name"] == "switch-core-bldg-a")
    assert "portal-gateway" in switch_dev["impacted_services"]
    assert "student-portal-ui" in switch_dev["impacted_services"]


@pytest.mark.asyncio
async def test_tracker_reflects_diagnostic_and_recovery_progression(
    client: AsyncClient, sre_user: tuple[User, str]
):
    """Verify tracker stages dynamically advance as diagnostics and recovery execute."""
    _, token = sre_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    # Round 1: Network diagnostic
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose",
        headers=headers,
        json={"tool_name": "network_connectivity_diagnostic"},
    )
    t1 = (await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/tracker", headers=headers)).json()
    assert t1["stages"][4]["status"] == "COMPLETED"  # Stage 5 Network Diagnostics

    # Round 2: Database diagnostic -> formulated plan
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/diagnose",
        headers=headers,
        json={"tool_name": "database_diagnostics"},
    )
    t2 = (await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/tracker", headers=headers)).json()
    assert t2["stages"][5]["status"] == "COMPLETED"  # Stage 6 Supporting diagnostics
    assert t2["stages"][9]["status"] == "BLOCKED"    # Stage 10 Awaiting approval

    # Approve recovery plan
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/approve",
        headers=headers,
        json={"decision": "approve"},
    )
    t3 = (await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/tracker", headers=headers)).json()
    assert t3["stages"][9]["status"] == "COMPLETED"  # Stage 10 Approved

    # Execute recovery and verify
    await client.post(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/execute-recovery",
        headers=headers,
        json={"force_verification_failure": False},
    )
    t4 = (await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}/investigation/tracker", headers=headers)).json()
    assert t4["stages"][10]["status"] == "COMPLETED"  # Stage 11 Action executed
    assert t4["stages"][11]["status"] == "COMPLETED"  # Stage 12 Telemetry verified
    assert t4["stages"][12]["status"] == "COMPLETED"  # Stage 13 Resolved

