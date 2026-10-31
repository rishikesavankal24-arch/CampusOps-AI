"""Automated test suite for VeriOps Phase 1: Incident Investigation Core.

Verifies:
- Seeding idempotency of multi-source demo telemetry.
- Strict chronological timeline sequencing by event_time ASC.
- Separation of event_time and ingest_time.
- Source type, severity, and service filtering.
- Dynamic service dependency graph with health metrics and evidence links.
- Versioned, traceable evidence bundle manifest generation.
- Security enforcement (401/403 unauthenticated rejections) and 404 error handling.
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.services.auth_service import create_access_token
from app.services.incident_service import DEMO_INCIDENT_ID


@pytest.fixture
async def auth_user(db_session: AsyncSession) -> tuple[User, str]:
    """Create an active student/support user and return (user, access_token)."""
    user = User(
        email="sre_investigator@campus.edu",
        name="SRE Investigator",
        role=UserRole.SUPPORT,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token, _ = create_access_token(user.id, user.email, user.role)
    return user, token


@pytest.mark.asyncio
async def test_unauthenticated_endpoints_rejected(client: AsyncClient):
    """Ensure all incident investigation endpoints require authentication."""
    endpoints = [
        ("POST", "/api/v1/incidents/seed-demo"),
        ("GET", "/api/v1/incidents"),
        ("GET", f"/api/v1/incidents/{DEMO_INCIDENT_ID}"),
        ("GET", f"/api/v1/incidents/{DEMO_INCIDENT_ID}/timeline"),
        ("GET", f"/api/v1/incidents/{DEMO_INCIDENT_ID}/graph"),
        ("GET", f"/api/v1/incidents/{DEMO_INCIDENT_ID}/evidence-bundle"),
    ]

    for method, path in endpoints:
        if method == "POST":
            response = await client.post(path)
        else:
            response = await client.get(path)
        # HTTPBearer returns 403 when header is missing or 401 when invalid
        assert response.status_code in (401, 403), f"Endpoint {path} failed auth requirement"


@pytest.mark.asyncio
async def test_seed_demo_incident(client: AsyncClient, auth_user: tuple[User, str]):
    """Ensure seeding creates the canonical demo incident and exactly 11 evidence items."""
    _, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post("/api/v1/incidents/seed-demo", headers=headers)
    assert response.status_code == 201
    data = response.json()

    assert data["id"] == str(DEMO_INCIDENT_ID)
    assert "504 Gateway Timeouts" in data["title"]
    assert data["priority"] == "critical"
    assert data["status"] == "investigating"
    assert data["evidence_count"] == 11
    assert data["simulated"] is True


@pytest.mark.asyncio
async def test_seed_demo_incident_idempotency(client: AsyncClient, auth_user: tuple[User, str]):
    """Ensure seeding multiple times is idempotent and does not create duplicate evidence."""
    _, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}

    # First seed
    res1 = await client.post("/api/v1/incidents/seed-demo", headers=headers)
    assert res1.status_code == 201
    assert res1.json()["evidence_count"] == 11

    # Second seed
    res2 = await client.post("/api/v1/incidents/seed-demo", headers=headers)
    assert res2.status_code == 201
    assert res2.json()["evidence_count"] == 11

    # List incidents: only 1 incident should exist
    list_res = await client.get("/api/v1/incidents", headers=headers)
    assert list_res.status_code == 200
    incidents = list_res.json()
    assert len(incidents) == 1
    assert incidents[0]["evidence_count"] == 11


@pytest.mark.asyncio
async def test_get_incident_by_id(client: AsyncClient, auth_user: tuple[User, str]):
    """Verify single incident retrieval and 404 for unknown IDs."""
    _, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}

    # Seed first
    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    # Valid ID
    res = await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}", headers=headers)
    assert res.status_code == 200
    assert res.json()["id"] == str(DEMO_INCIDENT_ID)

    # Non-existent ID
    random_id = uuid.uuid4()
    not_found = await client.get(f"/api/v1/incidents/{random_id}", headers=headers)
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_incident_timeline_ordering_and_timestamps(
    client: AsyncClient, auth_user: tuple[User, str]
):
    """Verify timeline events are strictly chronologically ordered by event_time and separate ingest_time."""
    _, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    res = await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}/timeline", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["incident_id"] == str(DEMO_INCIDENT_ID)
    assert data["total_events"] == 11
    assert data["filtered_events"] == 11
    assert len(data["events"]) == 11

    # Verify chronological sequence
    event_times = [datetime.fromisoformat(e["event_time"]) for e in data["events"]]
    for i in range(len(event_times) - 1):
        assert event_times[i] <= event_times[i + 1], "Events must be chronologically ordered"

    # Verify separation of event_time and ingest_time
    for ev in data["events"]:
        assert "event_time" in ev and ev["event_time"] is not None
        assert "ingest_time" in ev and ev["ingest_time"] is not None
        # Ingest time was recorded at seed time, event time was earlier (e.g. 09:00:00 UTC)
        ev_t = datetime.fromisoformat(ev["event_time"])
        ig_t = datetime.fromisoformat(ev["ingest_time"])
        assert ev_t != ig_t, "event_time and ingest_time must represent distinct moments"
        assert ev["simulated"] is True


@pytest.mark.asyncio
async def test_incident_timeline_filtering(client: AsyncClient, auth_user: tuple[User, str]):
    """Verify timeline filters by source_type, severity, and service_name."""
    _, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    # 1. Filter by source_type=application_log
    res_app_log = await client.get(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/timeline?source_type=application_log",
        headers=headers,
    )
    assert res_app_log.status_code == 200
    app_events = res_app_log.json()["events"]
    assert len(app_events) >= 1
    assert all(e["source_type"] == "application_log" for e in app_events)

    # 2. Filter by source_type=metric
    res_metric = await client.get(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/timeline?source_type=metric",
        headers=headers,
    )
    assert res_metric.status_code == 200
    metric_events = res_metric.json()["events"]
    assert len(metric_events) == 2  # db pool utilization and student login failure rate
    assert all(e["source_type"] == "metric" for e in metric_events)

    # 3. Filter by severity=critical
    res_crit = await client.get(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/timeline?severity=critical",
        headers=headers,
    )
    assert res_crit.status_code == 200
    crit_events = res_crit.json()["events"]
    assert len(crit_events) == 2  # P99 latency alert and student portal login failure rate
    assert all(e["severity"] == "critical" for e in crit_events)

    # 4. Filter by service_name=auth-service
    res_auth = await client.get(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/timeline?service_name=auth-service",
        headers=headers,
    )
    assert res_auth.status_code == 200
    auth_events = res_auth.json()["events"]
    assert len(auth_events) >= 3
    assert all(e["service_name"] == "auth-service" for e in auth_events)


@pytest.mark.asyncio
async def test_service_dependency_graph(client: AsyncClient, auth_user: tuple[User, str]):
    """Verify service dependency graph nodes, edges, root suspects, and evidence mapping."""
    _, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    res = await client.get(f"/api/v1/incidents/{DEMO_INCIDENT_ID}/graph", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["incident_id"] == str(DEMO_INCIDENT_ID)
    assert len(data["nodes"]) == 6
    assert len(data["edges"]) == 5

    # Check root suspects
    assert "auth-service" in data["root_suspects"]
    assert "campusops-db" in data["root_suspects"]

    # Check nodes have evidence mapping
    node_map = {n["id"]: n for n in data["nodes"]}
    assert "auth-service" in node_map
    assert node_map["auth-service"]["status"] == "critical"
    assert len(node_map["auth-service"]["supporting_evidence_ids"]) > 0

    assert "campusops-db" in node_map
    assert node_map["campusops-db"]["impact"] == "root_suspect"

    assert "student-portal-ui" in node_map
    assert node_map["student-portal-ui"]["service_type"] == "frontend"

    # Check edges
    edge_pairs = [(e["source"], e["target"]) for e in data["edges"]]
    assert ("student-portal-ui", "portal-gateway") in edge_pairs
    assert ("portal-gateway", "auth-service") in edge_pairs
    assert ("auth-service", "campusops-db") in edge_pairs


@pytest.mark.asyncio
async def test_evidence_bundle_manifest(client: AsyncClient, auth_user: tuple[User, str]):
    """Verify traceable evidence bundle manifest format and versioning."""
    _, token = auth_user
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/v1/incidents/seed-demo", headers=headers)

    res = await client.get(
        f"/api/v1/incidents/{DEMO_INCIDENT_ID}/evidence-bundle",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["incident_id"] == str(DEMO_INCIDENT_ID)
    assert data["bundle_version"] == "1.0.0"
    assert data["total_evidence_count"] == 11
    assert len(data["evidence_references"]) == 11
    assert len(data["timeline_summary"]) == 11
    assert len(data["affected_services"]) >= 4
    assert len(data["data_quality_notes"]) >= 2
    assert data["simulated"] is True

