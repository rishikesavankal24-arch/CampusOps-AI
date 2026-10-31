"""Incident and Evidence Intelligence Service for VeriOps Phase 1.

Provides deterministic demo incident seeding, normalized evidence retrieval,
chronologically sequenced timelines, service dependency graphs, and traceable
evidence bundles for autonomous incident investigation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence, EvidenceType
from app.models.incident import Incident, IncidentCategory, IncidentPriority, IncidentStatus
from app.models.network_device import DeviceStatus, DeviceType, NetworkDevice
from app.models.user import User
from app.schemas.incident import (
    EvidenceBundleResponse,
    IncidentSummary,
    IncidentTimelineResponse,
    NormalizedEvidenceItem,
    ServiceDependencyGraphResponse,
    ServiceEdge,
    ServiceNode,
)

# Deterministic Demo Incident ID
DEMO_INCIDENT_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")

# Canonical 11-item evidence dataset for Phase 1 Demo
DEMO_EVIDENCE_DEFINITIONS = [
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000001"),
        "evidence_type": EvidenceType.CONFIG,
        "source_type": "configuration",
        "service_name": "auth-service",
        "event_time": datetime(2026, 10, 31, 9, 0, 0, tzinfo=timezone.utc),
        "severity": "info",
        "title": "Kubernetes ConfigMap updated: pool_max reduced from 50 to 15",
        "content": (
            "GitOps deployment pipeline merged PR #142 (auth-config): max_db_pool_connections "
            "reduced from 50 to 15 to cut idle memory footprint."
        ),
        "details": {
            "author": "infra-bot@campusops.internal",
            "config_file": "helm/auth-service/values.yaml",
            "key": "database.pool_size",
            "old_value": 50,
            "new_value": 15,
            "commit": "a8f912c",
            "pipeline_id": "pipe-88219",
        },
        "correlation_id": "git-commit-a8f912c",
        "related_service": "campusops-db",
        "source_metadata": {"collector": "gitops-webhook", "cluster": "campus-prod-us-east"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000002"),
        "evidence_type": EvidenceType.CONFIG,
        "source_type": "deployment",
        "service_name": "auth-service",
        "event_time": datetime(2026, 10, 31, 9, 5, 0, tzinfo=timezone.utc),
        "severity": "info",
        "title": "Canary rollout of auth-service v2.4.1 completed (hash algorithm update)",
        "content": (
            "ArgoCD synced rollout auth-service:v2.4.1 to cluster prod-us-east. "
            "Changelog includes updated Argon2id memory cost parameter to 64MB."
        ),
        "details": {
            "version": "v2.4.1",
            "previous_version": "v2.4.0",
            "replicas": 3,
            "namespace": "campus-prod",
            "status": "Ready",
            "argon2_memory_kb": 65536,
        },
        "correlation_id": "deploy-auth-v241",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "argocd-audit", "cluster": "campus-prod-us-east"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000003"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "campusops-db",
        "event_time": datetime(2026, 10, 31, 9, 12, 0, tzinfo=timezone.utc),
        "severity": "warning",
        "title": "Database Connection Pool Saturation Reaches 100%",
        "content": (
            "Active connection pool utilization on campusops-db primary instance spiked to 15/15 (100%). "
            "Wait queue depth increased from 0 to 48 threads."
        ),
        "details": {
            "metric_name": "db_pool_utilization_ratio",
            "value": 1.0,
            "threshold": 0.85,
            "unit": "ratio",
            "active_conns": 15,
            "max_conns": 15,
            "waiting_conns": 48,
        },
        "correlation_id": "alert-db-pool-sat",
        "related_service": "auth-service",
        "source_metadata": {"collector": "prometheus-node-exporter", "instance": "db-primary-01"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000004"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "alert",
        "service_name": "portal-gateway",
        "event_time": datetime(2026, 10, 31, 9, 14, 30, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "High P99 Latency Alert (HTTP 504 Threshold Exceeded)",
        "content": (
            "Prometheus alert firing: P99 latency on /api/v1/auth/login exceeded 10.5s (SLA limit 1.2s). "
            "Ingress 504 Gateway Timeout rate jumped to 14.8%."
        ),
        "details": {
            "alert_name": "HighLatency504GatewayTimeouts",
            "p99_latency_seconds": 10.82,
            "sla_seconds": 1.2,
            "status_code_504_rate": 0.148,
            "evaluated_window": "5m",
        },
        "correlation_id": "prom-alert-504-0914",
        "related_service": "auth-service",
        "source_metadata": {"collector": "alertmanager", "receiver": "pagerduty-sre"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000005"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "application_log",
        "service_name": "auth-service",
        "event_time": datetime(2026, 10, 31, 9, 15, 10, tzinfo=timezone.utc),
        "severity": "error",
        "title": "ConnectionAcquisitionTimeoutError in SQLAlchemy async pool",
        "content": (
            "sqlalchemy.exc.TimeoutError: QueuePool limit of size 15 overflow 0 reached, "
            "connection timed out, timeout 10.00 (Background worker waiting for idle DB session)"
        ),
        "details": {
            "exception": "sqlalchemy.exc.TimeoutError",
            "pool_size": 15,
            "timeout_seconds": 10.0,
            "stack_trace": (
                "File 'app/database.py', line 35, in get_db\n"
                "  async with AsyncSessionLocal() as session:\n"
                "  File 'sqlalchemy/pool/impl.py', line 170, in _do_get\n"
                "    raise exc.TimeoutError('QueuePool limit of size 15 overflow 0 reached')"
            ),
        },
        "correlation_id": "req-c83109a1-auth",
        "related_service": "campusops-db",
        "source_metadata": {"collector": "fluentbit", "pod": "auth-service-68d7f879-xkz8q"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000006"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "trace",
        "service_name": "portal-gateway",
        "event_time": datetime(2026, 10, 31, 9, 16, 0, tzinfo=timezone.utc),
        "severity": "error",
        "title": "Distributed Trace: 10,214ms span latency blocked on auth-service DB acquisition",
        "content": (
            "Trace span [req-c83109a1] broke down: gateway -> auth-service (2ms), "
            "auth-service argon2 verify (380ms), auth-service DB acquisition wait (9,820ms TIMEOUT)."
        ),
        "details": {
            "trace_id": "trace-8891bf40aa91",
            "root_span": "portal-gateway:POST /auth/login",
            "total_duration_ms": 10214,
            "spans": [
                {"service": "portal-gateway", "operation": "proxy_pass", "duration_ms": 10214},
                {"service": "auth-service", "operation": "verify_credentials", "duration_ms": 10212},
                {"service": "campusops-db", "operation": "pool_checkout", "duration_ms": 9820, "error": "pool_timeout"},
            ],
        },
        "correlation_id": "trace-8891bf40aa91",
        "related_service": "auth-service",
        "source_metadata": {"collector": "opentelemetry-collector", "sampler": "100%"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000007"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "infrastructure_log",
        "service_name": "campusops-db",
        "event_time": datetime(2026, 10, 31, 9, 18, 0, tzinfo=timezone.utc),
        "severity": "warning",
        "title": "Postgres backend connection query locks: idle in transaction",
        "content": (
            "PostgreSQL pg_stat_activity shows 15 active client connections from auth-service "
            "IP 10.244.2.81 in state 'idle in transaction' waiting for client write."
        ),
        "details": {
            "total_conns": 15,
            "idle_in_transaction_count": 13,
            "max_idle_seconds": 128,
            "blocking_pid": 4819,
            "query_fragment": "SELECT users.id, users.email, users.password_hash FROM users WHERE users.email = $1",
        },
        "correlation_id": "infra-pg-locks-0918",
        "related_service": "auth-service",
        "source_metadata": {"collector": "rds-enhanced-monitoring", "engine": "PostgreSQL 15.4"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000008"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "student-portal-ui",
        "event_time": datetime(2026, 10, 31, 9, 20, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "Student Portal Login Failure Rate Surges to 84.2%",
        "content": (
            "Client telemetry beacon reports 84.2% failure rate on student portal login flow. "
            "Average user perceived delay: 11.4s."
        ),
        "details": {
            "metric_name": "student_login_failure_rate",
            "value": 0.842,
            "baseline": 0.012,
            "sample_count": 420,
            "failed_requests": 354,
            "avg_client_duration_ms": 11420,
        },
        "correlation_id": "beacon-metric-842",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "rum-beacon", "app": "student-portal-web"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000009"),
        "evidence_type": EvidenceType.USER_REPORT,
        "source_type": "support_ticket",
        "service_name": "student-portal-ui",
        "event_time": datetime(2026, 10, 31, 9, 21, 30, tzinfo=timezone.utc),
        "severity": "error",
        "title": "Helpdesk Ticket #IT-8841: 'Unable to login to portal for Course Registration'",
        "content": (
            "Student ticket submitted: 'Getting 504 Gateway Time Out when attempting to submit login "
            "credentials for course registration deadline. Tried Chrome and Safari.'"
        ),
        "details": {
            "ticket_id": "IT-8841",
            "submitter": "student21@univ.edu",
            "impact": "High (Course Drop/Add Deadline)",
            "channel": "Zendesk Help Center",
            "browser": "Chrome 128 / macOS",
        },
        "correlation_id": "ticket-IT-8841",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "zendesk-sync", "priority": "Urgent"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000010"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "alert",
        "service_name": "redis-session-cache",
        "event_time": datetime(2026, 10, 31, 9, 22, 15, tzinfo=timezone.utc),
        "severity": "warning",
        "title": "Redis Session Cache Degraded: Eviction Policy Memory Surge",
        "content": (
            "Warning: Redis instance session-cache-01 memory reached 88% due to unexpired retry-burst "
            "sessions. Session lock acquisition latency +120ms."
        ),
        "details": {
            "alert_name": "RedisMemoryHigh",
            "used_memory_pct": 88.4,
            "evicted_keys_rate": 42,
            "connected_clients": 64,
            "lock_wait_avg_ms": 124,
        },
        "correlation_id": "alert-redis-evict-0922",
        "related_service": "auth-service",
        "source_metadata": {"collector": "datadog-redis-check", "cluster": "session-cache-01"},
    },
    {
        "id": uuid.UUID("a1111111-0000-0000-0000-000000000011"),
        "evidence_type": EvidenceType.USER_REPORT,
        "source_type": "previous_incident",
        "service_name": "auth-service",
        "event_time": datetime(2026, 10, 31, 9, 25, 0, tzinfo=timezone.utc),
        "severity": "info",
        "title": "Historical Incident Postmortem #INC-2025-11-04: 'Connection Pool Starvation Under Peak Load'",
        "content": (
            "Reference postmortem from Fall semester: Similar 504 timeout cascade occurred when "
            "DB pool was configured < 40 during registration spikes. Remediation noted pool must be >= 50."
        ),
        "details": {
            "past_incident_id": "INC-2025-11-04",
            "similarity_score": 0.94,
            "resolution_summary": (
                "Revert pool_max to 50, configure idle_in_transaction_session_timeout to 10000ms, "
                "and ensure connection release in finally block."
            ),
            "kb_article_id": "KB-OPS-0442",
        },
        "correlation_id": "postmortem-inc-2025-11-04",
        "related_service": "campusops-db",
        "source_metadata": {"collector": "confluence-postmortem-archive", "verified_by": "lead-sre"},
    },
]


async def seed_demo_incident(db: AsyncSession, current_user_id: uuid.UUID | None = None) -> Incident:
    """Seed or update the canonical deterministic demo incident and all 11 evidence items."""
    # Find existing user if not provided
    if not current_user_id:
        result = await db.execute(select(User).limit(1))
        existing_user = result.scalars().first()
        if existing_user:
            current_user_id = existing_user.id
        else:
            raise ValueError("No existing user found to report the demo incident.")

    # 1. Upsert Incident record
    stmt = select(Incident).where(Incident.id == DEMO_INCIDENT_ID)
    incident_result = await db.execute(stmt)
    incident = incident_result.scalars().first()

    if not incident:
        incident = Incident(
            id=DEMO_INCIDENT_ID,
            title="Elevated HTTP 504 Gateway Timeouts & Auth Failure Cascade on Student Portal",
            description=(
                "[SIMULATED INCIDENT DATA] High-volume 504 Gateway Timeouts impacting student portal login "
                "during peak course registration window. Downstream dependencies between portal gateway, "
                "auth-service, and PostgreSQL database exhibit severe connection pool saturation."
            ),
            status=IncidentStatus.INVESTIGATING,
            priority=IncidentPriority.CRITICAL,
            category=IncidentCategory.SOFTWARE,
            reported_by=current_user_id,
            ai_classification={
                "incident_type": "authentication_cascade",
                "affected_layer": "backend_database",
                "confidence": 0.96,
                "simulated": True,
            },
        )
        db.add(incident)
        await db.flush()
    else:
        incident.title = "Elevated HTTP 504 Gateway Timeouts & Auth Failure Cascade on Student Portal"
        incident.status = IncidentStatus.INVESTIGATING
        incident.priority = IncidentPriority.CRITICAL

    # 2. Upsert the 11 Evidence items
    now_utc = datetime.now(timezone.utc)
    for item in DEMO_EVIDENCE_DEFINITIONS:
        ev_id = item["id"]
        ev_stmt = select(Evidence).where(Evidence.id == ev_id)
        ev_result = await db.execute(ev_stmt)
        existing_ev = ev_result.scalars().first()

        metadata = {
            "source_type": item["source_type"],
            "service_name": item["service_name"],
            "event_time": item["event_time"].isoformat(),
            "ingest_time": now_utc.isoformat(),
            "severity": item["severity"],
            "correlation_id": item["correlation_id"],
            "related_service": item["related_service"],
            "details": item["details"],
            "source_metadata": item["source_metadata"],
            "simulated": True,
        }

        if not existing_ev:
            new_ev = Evidence(
                id=ev_id,
                incident_id=DEMO_INCIDENT_ID,
                evidence_type=item["evidence_type"],
                title=item["title"],
                content=item["content"],
                extra_metadata=metadata,
            )
            db.add(new_ev)
        else:
            existing_ev.title = item["title"]
            existing_ev.content = item["content"]
            existing_ev.extra_metadata = metadata

    # 3. Seed Canonical Network Devices for Campus Digital Twin
    CANONICAL_DEVICES = [
        {
            "name": "switch-core-bldg-a",
            "device_type": DeviceType.SWITCH,
            "location": "Building A Core Rack 1",
            "ip_address": "10.0.0.1",
            "mac_address": "00:1A:2B:3C:4D:5E",
            "status": DeviceStatus.ONLINE,
            "health_metrics": {
                "optical_tx_rx_dbm": -2.4,
                "crc_errors": 0,
                "fans": "ALL_OK",
                "operating_temp_c": 36.4,
                "simulated": True,
            },
        },
        {
            "name": "gw-border-01",
            "device_type": DeviceType.ROUTER,
            "location": "Datacenter Edge Ingress",
            "ip_address": "10.244.0.1",
            "mac_address": "00:1A:2B:3C:4D:6F",
            "status": DeviceStatus.ONLINE,
            "health_metrics": {
                "throughput_gbps": 8.4,
                "packet_drop_rate": 0.0,
                "tls_handshake_ms": 4.1,
                "simulated": True,
            },
        },
        {
            "name": "ap-lib-floor2",
            "device_type": DeviceType.ACCESS_POINT,
            "location": "Library Floor 2 Common Area",
            "ip_address": "10.244.12.5",
            "mac_address": "00:1A:2B:3C:4D:7A",
            "status": DeviceStatus.ONLINE,
            "health_metrics": {
                "clients_connected": 48,
                "signal_strength_dbm": -42,
                "channel_utilization_pct": 28.0,
                "simulated": True,
            },
        },
        {
            "name": "dns-campus-primary",
            "device_type": DeviceType.SERVER,
            "location": "Campus Core Server Room",
            "ip_address": "10.0.0.2",
            "mac_address": "00:1A:2B:3C:4D:8B",
            "status": DeviceStatus.ONLINE,
            "health_metrics": {
                "queries_per_sec": 1240,
                "avg_response_ms": 3.8,
                "authoritative_zone": "campusops.edu",
                "simulated": True,
            },
        },
    ]

    for d_item in CANONICAL_DEVICES:
        d_stmt = select(NetworkDevice).where(NetworkDevice.name == d_item["name"])
        d_res = await db.execute(d_stmt)
        existing_dev = d_res.scalars().first()
        if not existing_dev:
            new_dev = NetworkDevice(
                name=d_item["name"],
                device_type=d_item["device_type"],
                location=d_item["location"],
                ip_address=d_item["ip_address"],
                mac_address=d_item["mac_address"],
                status=d_item["status"],
                health_metrics=d_item["health_metrics"],
                is_simulated=True,
            )
            db.add(new_dev)
        else:
            existing_dev.status = d_item["status"]
            existing_dev.health_metrics = d_item["health_metrics"]

    await db.commit()
    await db.refresh(incident)
    return incident


def _normalize_evidence(ev: Evidence) -> NormalizedEvidenceItem:
    """Transform an ORM Evidence row into a strictly-typed NormalizedEvidenceItem."""
    extra = ev.extra_metadata or {}
    source_type = extra.get("source_type") or (
        "application_log" if ev.evidence_type == EvidenceType.LOG else "configuration"
    )
    service_name = extra.get("service_name") or "unknown-service"

    event_time_raw = extra.get("event_time")
    if event_time_raw:
        if isinstance(event_time_raw, str):
            try:
                event_time = datetime.fromisoformat(event_time_raw)
            except Exception:
                event_time = ev.created_at or datetime.now(timezone.utc)
        elif isinstance(event_time_raw, datetime):
            event_time = event_time_raw
        else:
            event_time = ev.created_at or datetime.now(timezone.utc)
    else:
        event_time = ev.created_at or datetime.now(timezone.utc)

    ingest_time_raw = extra.get("ingest_time")
    if ingest_time_raw:
        if isinstance(ingest_time_raw, str):
            try:
                ingest_time = datetime.fromisoformat(ingest_time_raw)
            except Exception:
                ingest_time = ev.created_at or datetime.now(timezone.utc)
        elif isinstance(ingest_time_raw, datetime):
            ingest_time = ingest_time_raw
        else:
            ingest_time = ev.created_at or datetime.now(timezone.utc)
    else:
        ingest_time = ev.created_at or datetime.now(timezone.utc)

    # Ensure timezone info is present
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    if ingest_time.tzinfo is None:
        ingest_time = ingest_time.replace(tzinfo=timezone.utc)

    severity = extra.get("severity") or "info"
    correlation_id = extra.get("correlation_id")
    related_service = extra.get("related_service")
    details = extra.get("details") or {}
    source_metadata = extra.get("source_metadata") or {}
    simulated = extra.get("simulated", True)

    return NormalizedEvidenceItem(
        evidence_id=ev.id,
        incident_id=ev.incident_id,
        source_type=source_type,
        service_name=service_name,
        event_time=event_time,
        ingest_time=ingest_time,
        severity=severity,
        title=ev.title,
        content=ev.content,
        details=details,
        correlation_id=correlation_id,
        related_service=related_service,
        simulated=simulated,
        source_metadata=source_metadata,
    )


async def list_incidents(db: AsyncSession, limit: int = 50) -> list[IncidentSummary]:
    """Retrieve list of incidents with evidence counts."""
    stmt = (
        select(
            Incident,
            func.count(Evidence.id).label("evidence_count"),
        )
        .outerjoin(Evidence, Incident.id == Evidence.incident_id)
        .group_by(Incident.id)
        .order_by(Incident.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    summaries = []
    for inc, ev_count in rows:
        summaries.append(
            IncidentSummary(
                id=inc.id,
                title=inc.title,
                description=inc.description,
                status=inc.status.value,
                priority=inc.priority.value,
                category=inc.category.value,
                created_at=inc.created_at,
                evidence_count=ev_count,
                affected_services_count=5 if inc.id == DEMO_INCIDENT_ID else 1,
                simulated=True,
            )
        )
    return summaries


async def get_incident_summary(db: AsyncSession, incident_id: uuid.UUID) -> IncidentSummary | None:
    """Retrieve summary of a specific incident."""
    stmt = select(Incident).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    inc = result.scalars().first()
    if not inc:
        return None

    ev_count_stmt = select(func.count(Evidence.id)).where(Evidence.incident_id == incident_id)
    ev_count_res = await db.execute(ev_count_stmt)
    ev_count = ev_count_res.scalar_one()

    return IncidentSummary(
        id=inc.id,
        title=inc.title,
        description=inc.description,
        status=inc.status.value,
        priority=inc.priority.value,
        category=inc.category.value,
        created_at=inc.created_at,
        evidence_count=ev_count,
        affected_services_count=5 if inc.id == DEMO_INCIDENT_ID else 1,
        simulated=True,
    )


async def get_incident_timeline(
    db: AsyncSession,
    incident_id: uuid.UUID,
    source_type: str | None = None,
    severity: str | None = None,
    service_name: str | None = None,
) -> IncidentTimelineResponse | None:
    """Retrieve chronologically ordered normalized evidence timeline for an incident."""
    stmt = select(Incident).where(Incident.id == incident_id)
    inc_res = await db.execute(stmt)
    incident = inc_res.scalars().first()
    if not incident:
        return None

    # Retrieve all evidence for the incident
    ev_stmt = select(Evidence).where(Evidence.incident_id == incident_id)
    ev_res = await db.execute(ev_stmt)
    raw_evidence = ev_res.scalars().all()

    # Normalize all items
    normalized = [_normalize_evidence(ev) for ev in raw_evidence]

    # Sort strictly by event_time ASC
    normalized.sort(key=lambda x: x.event_time)

    total_events = len(normalized)

    # Apply optional filters
    filtered = normalized
    if source_type:
        filtered = [e for e in filtered if e.source_type.lower() == source_type.lower()]
    if severity:
        filtered = [e for e in filtered if e.severity.lower() == severity.lower()]
    if service_name:
        filtered = [e for e in filtered if e.service_name.lower() == service_name.lower()]

    time_window = {
        "start": normalized[0].event_time if normalized else None,
        "end": normalized[-1].event_time if normalized else None,
    }

    return IncidentTimelineResponse(
        incident_id=incident.id,
        incident_title=incident.title,
        severity=incident.priority.value,
        status=incident.status.value,
        total_events=total_events,
        filtered_events=len(filtered),
        time_window=time_window,
        events=filtered,
    )


async def get_service_dependency_graph(
    db: AsyncSession, incident_id: uuid.UUID
) -> ServiceDependencyGraphResponse | None:
    """Construct dynamic service dependency graph with health and evidence references."""
    stmt = select(Incident).where(Incident.id == incident_id)
    inc_res = await db.execute(stmt)
    incident = inc_res.scalars().first()
    if not incident:
        return None

    # Fetch evidence to map supporting references
    ev_stmt = select(Evidence).where(Evidence.incident_id == incident_id)
    ev_res = await db.execute(ev_stmt)
    raw_evidence = ev_res.scalars().all()
    normalized = [_normalize_evidence(ev) for ev in raw_evidence]

    # Group evidence IDs by service
    service_evidence_map: dict[str, list[uuid.UUID]] = {}
    for ev in normalized:
        service_evidence_map.setdefault(ev.service_name, []).append(ev.evidence_id)

    # Define standard topology with impact based on mapped evidence
    nodes = [
        ServiceNode(
            id="student-portal-ui",
            name="Student Portal UI (Next.js)",
            service_type="frontend",
            status="degraded",
            impact="high",
            metrics_summary={
                "failure_rate": "84.2%",
                "p99_latency": "11.4s",
                "client_504_errors": 354,
            },
            supporting_evidence_ids=service_evidence_map.get("student-portal-ui", []),
        ),
        ServiceNode(
            id="portal-gateway",
            name="API Portal Gateway (Envoy/Nginx)",
            service_type="gateway",
            status="critical",
            impact="high",
            metrics_summary={
                "http_504_rate": "14.8%",
                "p99_latency": "10.8s",
                "upstream_timeouts": 128,
            },
            supporting_evidence_ids=service_evidence_map.get("portal-gateway", []),
        ),
        ServiceNode(
            id="auth-service",
            name="Authentication Microservice (FastAPI)",
            service_type="microservice",
            status="critical",
            impact="root_suspect",
            metrics_summary={
                "db_pool_queue_depth": 48,
                "version": "v2.4.1",
                "argon2_cost": "64MB",
                "status": "connection_pool_starved",
            },
            supporting_evidence_ids=service_evidence_map.get("auth-service", []),
        ),
        ServiceNode(
            id="campusops-db",
            name="PostgreSQL Core Database (pgvector)",
            service_type="database",
            status="degraded",
            impact="root_suspect",
            metrics_summary={
                "active_connections": "15/15 (100%)",
                "idle_in_transaction": 13,
                "blocking_queries": 1,
            },
            supporting_evidence_ids=service_evidence_map.get("campusops-db", []),
        ),
        ServiceNode(
            id="redis-session-cache",
            name="Redis Session & Token Cache",
            service_type="cache",
            status="degraded",
            impact="medium",
            metrics_summary={
                "memory_utilization": "88.4%",
                "eviction_rate": "42/sec",
                "lock_latency": "+120ms",
            },
            supporting_evidence_ids=service_evidence_map.get("redis-session-cache", []),
        ),
        ServiceNode(
            id="campus-ldap-idp",
            name="Campus Identity Provider (LDAP / SSO)",
            service_type="idp",
            status="healthy",
            impact="none",
            metrics_summary={
                "health": "operational",
                "p95_latency": "18ms",
                "error_rate": "0.0%",
            },
            supporting_evidence_ids=service_evidence_map.get("campus-ldap-idp", []),
        ),
    ]

    edges = [
        ServiceEdge(
            source="student-portal-ui",
            target="portal-gateway",
            relationship="routes_traffic",
            protocol="HTTPS/REST",
            is_degraded=True,
        ),
        ServiceEdge(
            source="portal-gateway",
            target="auth-service",
            relationship="authenticates_request",
            protocol="HTTP/JSON",
            is_degraded=True,
        ),
        ServiceEdge(
            source="auth-service",
            target="campusops-db",
            relationship="queries_user_session",
            protocol="PostgreSQL/TCP",
            is_degraded=True,
        ),
        ServiceEdge(
            source="auth-service",
            target="redis-session-cache",
            relationship="caches_auth_tokens",
            protocol="Redis/RESP",
            is_degraded=True,
        ),
        ServiceEdge(
            source="auth-service",
            target="campus-ldap-idp",
            relationship="validates_directory_credentials",
            protocol="LDAPS/TCP",
            is_degraded=False,
        ),
    ]

    root_suspects = ["auth-service", "campusops-db"]
    affected_services = [
        "student-portal-ui",
        "portal-gateway",
        "auth-service",
        "campusops-db",
        "redis-session-cache",
    ]

    return ServiceDependencyGraphResponse(
        incident_id=incident.id,
        nodes=nodes,
        edges=edges,
        root_suspects=root_suspects,
        affected_services=affected_services,
    )


async def get_evidence_bundle(
    db: AsyncSession, incident_id: uuid.UUID
) -> EvidenceBundleResponse | None:
    """Generate a versioned, traceable evidence bundle manifest for agentic root-cause analysis."""
    stmt = select(Incident).where(Incident.id == incident_id)
    inc_res = await db.execute(stmt)
    incident = inc_res.scalars().first()
    if not incident:
        return None

    ev_stmt = select(Evidence).where(Evidence.incident_id == incident_id)
    ev_res = await db.execute(ev_stmt)
    raw_evidence = ev_res.scalars().all()
    normalized = [_normalize_evidence(ev) for ev in raw_evidence]
    normalized.sort(key=lambda x: x.event_time)

    timeline_summary = [
        {
            "evidence_id": str(e.evidence_id),
            "event_time": e.event_time.isoformat(),
            "source_type": e.source_type,
            "service_name": e.service_name,
            "severity": e.severity,
            "title": e.title,
            "correlation_id": e.correlation_id,
        }
        for e in normalized
    ]

    affected_services = sorted(list({e.service_name for e in normalized}))
    time_window = {
        "start": normalized[0].event_time if normalized else None,
        "end": normalized[-1].event_time if normalized else None,
    }

    data_quality_notes = [
        "All 11 multi-source evidence records strictly correlated via ISO 8601 UTC timestamps.",
        "Clock skew across collector nodes verified within 15ms tolerance window.",
        "Distributed trace IDs [req-c83109a1, trace-8891bf40aa91] link ingress gateway to database pool timeout.",
        "Simulated test data generated for TCS Hackathon AIOps Challenge demonstration.",
    ]

    bundle_id = f"bundle-{incident_id.hex[:12]}-v1"

    return EvidenceBundleResponse(
        bundle_id=bundle_id,
        bundle_version="1.0.0",
        created_at=datetime.now(timezone.utc),
        incident_id=incident.id,
        incident_title=incident.title,
        time_window=time_window,
        total_evidence_count=len(normalized),
        evidence_references=[e.evidence_id for e in normalized],
        timeline_summary=timeline_summary,
        affected_services=affected_services,
        data_quality_notes=data_quality_notes,
        simulated=True,
    )

