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

# Deterministic Multi-Scenario Demo Incident IDs
SCENARIO_1_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
NET_SCENARIO_1_ID = uuid.UUID("44444444-2222-3333-4444-555555555555")
SCENARIO_2_ID = uuid.UUID("22222222-2222-3333-4444-555555555555")
SCENARIO_3_ID = uuid.UUID("33333333-2222-3333-4444-555555555555")
DEMO_INCIDENT_ID = SCENARIO_1_ID

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

# Scenario 1 (MTU Mismatch) Evidence: Core Switch Trunk MTU Mismatch (Network Hardware)
SCENARIO_MTU_EVIDENCE_DEFINITIONS = [
    {
        "id": uuid.UUID("d4444444-0000-0000-0000-000000000001"),
        "evidence_type": EvidenceType.CONFIG,
        "source_type": "configuration",
        "service_name": "switch-core-bldg-a",
        "event_time": datetime(2026, 10, 31, 9, 0, 0, tzinfo=timezone.utc),
        "severity": "warning",
        "title": "GitOps Network Config Push: Interface Te1/0/1 Reset to Default MTU 1500",
        "content": (
            "Ansible automation play 'campus-switch-provisioning' pushed commit c718a2f resetting "
            "switch-core-bldg-a:Te1/0/1 to default campus template (MTU: 1500) rather than jumbo trunk profile (9216)."
        ),
        "details": {
            "device": "switch-core-bldg-a",
            "interface": "TenGigabitEthernet1/0/1",
            "old_mtu": 9216,
            "new_mtu": 1500,
            "vlan": 100,
            "commit": "c718a2f",
            "author": "netops-automation@campusops.internal",
        },
        "correlation_id": "gitops-net-c718a2f",
        "related_service": "switch-dist-bldg-b",
        "source_metadata": {"collector": "ansible-netconf-audit", "host": "switch-core-bldg-a"},
    },
    {
        "id": uuid.UUID("d4444444-0000-0000-0000-000000000002"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "switch-dist-bldg-b",
        "event_time": datetime(2026, 10, 31, 9, 4, 0, tzinfo=timezone.utc),
        "severity": "info",
        "title": "Peer Trunk Interface Eth1/1 Configured for MTU 9216 (Jumbo Frames)",
        "content": (
            "Distribution switch switch-dist-bldg-b interface Eth1/1 peer link active with MTU 9216, "
            "transmitting 8,800-byte jumbo frames across VLAN 100."
        ),
        "details": {
            "device": "switch-dist-bldg-b",
            "interface": "Ethernet1/1",
            "configured_mtu": 9216,
            "jumbo_enabled": True,
        },
        "correlation_id": "snmp-mtu-check-0904",
        "related_service": "switch-core-bldg-a",
        "source_metadata": {"collector": "telemetry-agent", "host": "switch-dist-bldg-b"},
    },
    {
        "id": uuid.UUID("d4444444-0000-0000-0000-000000000003"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "infrastructure_log",
        "service_name": "switch-core-bldg-a",
        "event_time": datetime(2026, 10, 31, 9, 8, 0, tzinfo=timezone.utc),
        "severity": "error",
        "title": "Kernel Syslog: %ETH-4-PACKET_OVERSIZE Frames Exceeding MTU Discarded",
        "content": (
            "switch-core-bldg-a kernel log: %ETH-4-PACKET_OVERSIZE: Interface Te1/0/1 discarded "
            "1,482 incoming frames exceeding configured MTU of 1500 bytes."
        ),
        "details": {
            "facility": "ETH",
            "severity": 4,
            "mnemonic": "PACKET_OVERSIZE",
            "dropped_frames": 1482,
            "interface": "Te1/0/1",
        },
        "correlation_id": "syslog-oversize-0908",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "rsyslog-collector", "facility": "local7"},
    },
    {
        "id": uuid.UUID("d4444444-0000-0000-0000-000000000004"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "switch-core-bldg-a",
        "event_time": datetime(2026, 10, 31, 9, 16, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "ICMP MTU Sweep with DF Bit: 1472B PASS (0% Loss), 1500B FAIL (100% Loss)",
        "content": (
            "Network probe diagnostic: ICMP echo with Don't Fragment (DF) bit set passes up to 1472 bytes "
            "(IP packet 1500 bytes). Echo with 1500+ bytes payload fails with 100% packet loss (Path MTU Blackhole)."
        ),
        "details": {
            "ping_64b_loss": 0.0,
            "ping_1472b_loss": 0.0,
            "ping_1500b_loss": 100.0,
            "df_bit": True,
            "icmp_type3_code4_status": "DROPPED",
        },
        "correlation_id": "ping-df-sweep-0916",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "blackbox-exporter", "target": "switch-core-bldg-a"},
    },
    {
        "id": uuid.UUID("d4444444-0000-0000-0000-000000000005"),
        "evidence_type": EvidenceType.USER_REPORT,
        "source_type": "support_ticket",
        "service_name": "student-portal-ui",
        "event_time": datetime(2026, 10, 31, 9, 20, 0, tzinfo=timezone.utc),
        "severity": "error",
        "title": "Helpdesk Ticket #IT-8841: 'Unable to login to portal for Course Registration'",
        "content": (
            "Student ticket submitted: 'Getting 504 Gateway Time Out when attempting to submit login "
            "credentials for course registration deadline. Small test pages load, but submit fails.'"
        ),
        "details": {
            "ticket_id": "IT-8841",
            "submitter": "student21@univ.edu",
            "impact": "High (Course Drop/Add Deadline)",
            "channel": "Zendesk Help Center",
        },
        "correlation_id": "ticket-IT-8841",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "zendesk-sync", "priority": "Urgent"},
    },
]

# Scenario 2 Evidence: Campus Wi-Fi & DHCP Pool Exhaustion (Network Hardware)
SCENARIO_2_EVIDENCE_DEFINITIONS = [
    {
        "id": uuid.UUID("b2222222-0000-0000-0000-000000000001"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "ap-lib-floor2",
        "event_time": datetime(2026, 10, 31, 9, 8, 0, tzinfo=timezone.utc),
        "severity": "warning",
        "title": "Access Point RF Channel Saturation & Client Association Spike",
        "content": (
            "Access point ap-lib-floor2 (Library 2nd Floor) reached 128 active client associations "
            "(rated limit: 100). 5GHz channel 36 utilization spiked to 94.2% with severe RF interference."
        ),
        "details": {
            "device": "ap-lib-floor2",
            "active_clients": 128,
            "max_clients": 100,
            "channel_utilization_pct": 94.2,
            "rf_band": "5GHz (Channel 36)",
            "snr_db": 12.4,
        },
        "correlation_id": "wifi-rf-sat-0908",
        "related_service": "student-portal-ui",
        "source_metadata": {"collector": "cisco-catalyst-center", "location": "Library Floor 2"},
    },
    {
        "id": uuid.UUID("b2222222-0000-0000-0000-000000000002"),
        "evidence_type": EvidenceType.CONFIG,
        "source_type": "alert",
        "service_name": "gw-border-01",
        "event_time": datetime(2026, 10, 31, 9, 11, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "DHCP Scope Exhaustion on Subnet 10.0.4.0/24 (0 Available Leases)",
        "content": (
            "Core DHCP server pool for wireless subnet 10.0.4.0/24 reached 100% capacity "
            "(254/254 active leases). DHCPDISCOVER requests from 42 mobile clients rejected."
        ),
        "details": {
            "subnet": "10.0.4.0/24",
            "total_addresses": 254,
            "allocated_leases": 254,
            "available_leases": 0,
            "exhaustion_ratio": 1.0,
            "dhcp_server": "10.0.0.53",
        },
        "correlation_id": "dhcp-scope-exhaust-0911",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "infoblox-ipam-syslog", "severity": "ALERT"},
    },
    {
        "id": uuid.UUID("b2222222-0000-0000-0000-000000000003"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "application_log",
        "service_name": "student-portal-ui",
        "event_time": datetime(2026, 10, 31, 9, 14, 0, tzinfo=timezone.utc),
        "severity": "error",
        "title": "Client Connection Timed Out: Unable to Reach Gateway",
        "content": (
            "Student portal web client logs report unresolvable host 'portal.campusops.edu' "
            "and socket timeout. Operating system reports no IPv4 default route assigned."
        ),
        "details": {
            "error_code": "ERR_NAME_NOT_RESOLVED",
            "network_state": "DHCP_FAILED",
            "affected_client_os": "macOS / iOS / Android",
            "client_ip": "169.254.12.88 (APIPA Self-Assigned)",
        },
        "correlation_id": "client-apipa-timeout-0914",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "sentry-browser-rum", "environment": "production"},
    },
    {
        "id": uuid.UUID("b2222222-0000-0000-0000-000000000004"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "switch-core-bldg-a",
        "event_time": datetime(2026, 10, 31, 9, 16, 0, tzinfo=timezone.utc),
        "severity": "warning",
        "title": "Access Point Uplink Port Packet Drops Surge to 24.8%",
        "content": (
            "Switch port GigabitEthernet1/0/18 (connecting ap-lib-floor2) reports 24.8% ingress packet "
            "drop rate due to buffer overruns during peak registration login traffic."
        ),
        "details": {
            "switch": "switch-core-bldg-a",
            "port": "GigabitEthernet1/0/18",
            "rx_dropped_pct": 24.8,
            "tx_packets_sec": 1420,
            "queue_drops": 4820,
        },
        "correlation_id": "switch-port-drops-0916",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "snmp-collector", "host": "switch-core-bldg-a"},
    },
    {
        "id": uuid.UUID("b2222222-0000-0000-0000-000000000005"),
        "evidence_type": EvidenceType.USER_REPORT,
        "source_type": "support_ticket",
        "service_name": "student-portal-ui",
        "event_time": datetime(2026, 10, 31, 9, 18, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "Helpdesk Ticket #IT-8890: 'Wi-Fi drops in Library; Cannot Submit Course Registration'",
        "content": (
            "Urgent student ticket: 'Wi-Fi in Library 2nd floor connects but says No Internet Connection. "
            "Laptop gets IP 169.254.x.x. Course drop/add window closes in 30 minutes.'"
        ),
        "details": {
            "ticket_id": "IT-8890",
            "submitter": "k.patel@univ.edu",
            "location": "Library Floor 2 Quiet Study Room",
            "urgency": "High",
        },
        "correlation_id": "ticket-IT-8890",
        "related_service": "student-portal-ui",
        "source_metadata": {"collector": "zendesk-sync", "priority": "Urgent"},
    },
]

# Scenario 3 Evidence: Border Gateway BGP Route Flapping & Edge Firewall Policy Drift (Network Perimeter)
SCENARIO_3_EVIDENCE_DEFINITIONS = [
    {
        "id": uuid.UUID("c3333333-0000-0000-0000-000000000001"),
        "evidence_type": EvidenceType.CONFIG,
        "source_type": "configuration",
        "service_name": "firewall-edge-01",
        "event_time": datetime(2026, 10, 31, 9, 2, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "Firewall Rule Drift: SEC-POLICY-BLOCK-UNREGISTERED Shadowed Outbound Transit",
        "content": (
            "Palo Alto firewall security commit pushed rule #118 'SEC-POLICY-BLOCK-UNREGISTERED' above rule #124 "
            "'PERMIT-ACADEMIC-EGRESS', inadvertently dropping 4,280 legitimate outbound sessions per minute."
        ),
        "details": {
            "firewall": "firewall-edge-01",
            "shadowed_rule": "PERMIT-ACADEMIC-EGRESS (#124)",
            "shadowing_rule": "SEC-POLICY-BLOCK-UNREGISTERED (#118)",
            "action": "DROP",
            "author": "secops-bot@campusops.internal",
        },
        "correlation_id": "fw-drift-commit-0902",
        "related_service": "gw-border-01",
        "source_metadata": {"collector": "panos-api-audit", "device": "firewall-edge-01"},
    },
    {
        "id": uuid.UUID("c3333333-0000-0000-0000-000000000002"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "infrastructure_log",
        "service_name": "gw-border-01",
        "event_time": datetime(2026, 10, 31, 9, 5, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "BGP Peer Flapping: %BGP-5-ADJCHANGE Neighbor 198.51.100.1 Down (Hold Timer Expired)",
        "content": (
            "Cisco ISR 4451 syslog: %BGP-5-ADJCHANGE: neighbor 198.51.100.1 Down - BGP hold timer expired. "
            "Primary ISP transit flapped 14 times in past 25 minutes, causing WAN prefix table oscillations."
        ),
        "details": {
            "router": "gw-border-01",
            "neighbor": "198.51.100.1 (AS1299-Primary)",
            "flap_count": 14,
            "hold_timer_seconds": 90,
            "secondary_neighbor": "203.0.113.2 (AS2914-Secondary)",
        },
        "correlation_id": "bgp-flap-adjchange-0905",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "syslog-collector", "host": "gw-border-01"},
    },
    {
        "id": uuid.UUID("c3333333-0000-0000-0000-000000000003"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "firewall-edge-01",
        "event_time": datetime(2026, 10, 31, 9, 10, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "Edge Firewall Egress Drops Surge to 4,280 Sessions/Min",
        "content": (
            "Palo Alto PA-3220 active traffic log: 4,280 dropped egress sessions/minute on zone 'campus-trust' "
            "to 'internet-untrust' with reason DROP_SECURITY_POLICY_DENY."
        ),
        "details": {
            "dropped_sessions_min": 4280,
            "zone_from": "campus-trust",
            "zone_to": "internet-untrust",
            "reason": "DROP_SECURITY_POLICY_DENY",
        },
        "correlation_id": "fw-metric-drops-0910",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "panos-metrics-exporter", "device": "firewall-edge-01"},
    },
    {
        "id": uuid.UUID("c3333333-0000-0000-0000-000000000004"),
        "evidence_type": EvidenceType.LOG,
        "source_type": "metric",
        "service_name": "gw-border-01",
        "event_time": datetime(2026, 10, 31, 9, 13, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "WAN Egress Packet Loss Spikes to 31.4% (Latency 3,200ms)",
        "content": (
            "Border gateway blackbox probe: WAN egress packet loss jumped to 31.4%. Round-trip latency "
            "to external DNS (8.8.8.8) swinging between 14ms and 3,200ms due to BGP route hunting."
        ),
        "details": {
            "packet_loss_pct": 31.4,
            "avg_latency_ms": 3200,
            "target": "8.8.8.8",
            "route_convergence_sec": 48.2,
        },
        "correlation_id": "wan-probe-loss-0913",
        "related_service": "portal-gateway",
        "source_metadata": {"collector": "blackbox-exporter", "target": "gw-border-01"},
    },
    {
        "id": uuid.UUID("c3333333-0000-0000-0000-000000000005"),
        "evidence_type": EvidenceType.USER_REPORT,
        "source_type": "alert",
        "service_name": "portal-gateway",
        "event_time": datetime(2026, 10, 31, 9, 15, 0, tzinfo=timezone.utc),
        "severity": "critical",
        "title": "AlertManager P1: WAN_CONNECTIVITY_DEGRADED & Ingress 504 Timeout Spike",
        "content": (
            "P1 Network Incident: Outbound academic SaaS, external student auth callbacks, and internet "
            "connectivity degraded campus-wide due to concurrent BGP flap and firewall policy drop."
        ),
        "details": {
            "alert": "P1_WAN_CONNECTIVITY_DEGRADED",
            "gateway_504_pct": 38.6,
            "pagerduty_incident": "PD-NET-88219",
        },
        "correlation_id": "alert-wan-degraded-0915",
        "related_service": "gw-border-01",
        "source_metadata": {"collector": "alertmanager", "receiver": "pagerduty-netops"},
    },
]


async def seed_demo_incident(
    db: AsyncSession,
    current_user_id: uuid.UUID | None = None,
    target_scenario_id: uuid.UUID | None = None,
) -> Incident:
    """Seed or update the canonical deterministic demo incident scenarios and evidence items."""
    # Find existing user if not provided
    if not current_user_id:
        result = await db.execute(select(User).limit(1))
        existing_user = result.scalars().first()
        if existing_user:
            current_user_id = existing_user.id
        else:
            raise ValueError("No existing user found to report the demo incident.")

    target_id = target_scenario_id or SCENARIO_1_ID
    target_incident = None

    # Upsert only the requested scenario so canonical tests expecting single-incident remain 100% passing
    if target_id == NET_SCENARIO_1_ID:
        stmt_mtu = select(Incident).where(Incident.id == NET_SCENARIO_1_ID)
        res_mtu = await db.execute(stmt_mtu)
        inc_mtu = res_mtu.scalars().first()
        if not inc_mtu:
            inc_mtu = Incident(
                id=NET_SCENARIO_1_ID,
                title="Campus Core Switch Trunk MTU Mismatch & 802.1Q Frame Drops",
                description=(
                    "[SIMULATED INCIDENT DATA] High-volume 504 Gateway Timeouts impacting student portal login "
                    "during peak course registration window. Inter-building 802.1Q trunk interface Te1/0/1 on switch-core-bldg-a "
                    "was accidentally configured with standard MTU 1500 bytes while peer interface Eth1/1 uses MTU 9216 Jumbo frames, "
                    "causing 100% packet loss on payloads exceeding 1472 bytes."
                ),
                status=IncidentStatus.INVESTIGATING,
                priority=IncidentPriority.CRITICAL,
                category=IncidentCategory.NETWORK,
                reported_by=current_user_id,
                ai_classification={
                    "incident_type": "core_switch_mtu_mismatch",
                    "affected_layer": "campus_network_backbone",
                    "confidence": 0.98,
                    "simulated": True,
                },
            )
            db.add(inc_mtu)
        else:
            inc_mtu.title = "Campus Core Switch Trunk MTU Mismatch & 802.1Q Frame Drops"
            inc_mtu.status = IncidentStatus.INVESTIGATING
            inc_mtu.priority = IncidentPriority.CRITICAL
            inc_mtu.category = IncidentCategory.NETWORK
            inc_mtu.ai_root_cause = None
            inc_mtu.ai_resolution = None
            inc_mtu.resolved_at = None
        target_incident = inc_mtu

    elif target_id == SCENARIO_1_ID:
        stmt1 = select(Incident).where(Incident.id == SCENARIO_1_ID)
        res1 = await db.execute(stmt1)
        inc1 = res1.scalars().first()
        if not inc1:
            inc1 = Incident(
                id=SCENARIO_1_ID,
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
            db.add(inc1)
        else:
            inc1.title = "Elevated HTTP 504 Gateway Timeouts & Auth Failure Cascade on Student Portal"
            inc1.status = IncidentStatus.INVESTIGATING
            inc1.priority = IncidentPriority.CRITICAL
            inc1.category = IncidentCategory.SOFTWARE
            inc1.ai_root_cause = None
            inc1.ai_resolution = None
            inc1.resolved_at = None
        target_incident = inc1

    elif target_id == SCENARIO_2_ID:
        stmt2 = select(Incident).where(Incident.id == SCENARIO_2_ID)
        res2 = await db.execute(stmt2)
        inc2 = res2.scalars().first()
        if not inc2:
            inc2 = Incident(
                id=SCENARIO_2_ID,
                title="Campus Wi-Fi Ingress Degradation & DHCP Scope Exhaustion (Library Zone)",
                description=(
                    "[SIMULATED INCIDENT DATA] Student portal completely inaccessible for students on campus wireless "
                    "in Library Floor 2. Heavy client association spike reached 128 clients on AP ap-lib-floor2, "
                    "causing 94.2% RF saturation and total exhaustion of DHCP subnet 10.0.4.0/24 leases."
                ),
                status=IncidentStatus.INVESTIGATING,
                priority=IncidentPriority.HIGH,
                category=IncidentCategory.NETWORK,
                reported_by=current_user_id,
                ai_classification={
                    "incident_type": "wifi_dhcp_exhaustion",
                    "affected_layer": "campus_network_hardware",
                    "confidence": 0.98,
                    "simulated": True,
                },
            )
            db.add(inc2)
        else:
            inc2.title = "Campus Wi-Fi Ingress Degradation & DHCP Scope Exhaustion (Library Zone)"
            inc2.status = IncidentStatus.INVESTIGATING
            inc2.priority = IncidentPriority.HIGH
            inc2.category = IncidentCategory.NETWORK
            inc2.ai_root_cause = None
            inc2.ai_resolution = None
            inc2.resolved_at = None
        target_incident = inc2

    elif target_id == SCENARIO_3_ID:
        stmt3 = select(Incident).where(Incident.id == SCENARIO_3_ID)
        res3 = await db.execute(stmt3)
        inc3 = res3.scalars().first()
        if not inc3:
            inc3 = Incident(
                id=SCENARIO_3_ID,
                title="Border Gateway BGP Route Flapping & Edge Firewall Policy Drift",
                description=(
                    "[SIMULATED INCIDENT DATA] Critical outbound connectivity failure across campus network. "
                    "Primary upstream ISP BGP neighbor 198.51.100.1 flapped 14 times due to hold-timer expiry, "
                    "and Edge Firewall rule #118 shadowed outbound academic transit, dropping 4,280 sessions/minute."
                ),
                status=IncidentStatus.INVESTIGATING,
                priority=IncidentPriority.CRITICAL,
                category=IncidentCategory.NETWORK,
                reported_by=current_user_id,
                ai_classification={
                    "incident_type": "bgp_routing_firewall_drift",
                    "affected_layer": "border_wan_network",
                    "confidence": 0.98,
                    "simulated": True,
                },
            )
            db.add(inc3)
        else:
            inc3.title = "Border Gateway BGP Route Flapping & Edge Firewall Policy Drift"
            inc3.description = (
                "[SIMULATED INCIDENT DATA] Critical outbound connectivity failure across campus network. "
                "Primary upstream ISP BGP neighbor 198.51.100.1 flapped 14 times due to hold-timer expiry, "
                "and Edge Firewall rule #118 shadowed outbound academic transit, dropping 4,280 sessions/minute."
            )
            inc3.status = IncidentStatus.INVESTIGATING
            inc3.priority = IncidentPriority.CRITICAL
            inc3.category = IncidentCategory.NETWORK
            inc3.ai_root_cause = None
            inc3.ai_resolution = None
            inc3.resolved_at = None
        target_incident = inc3

    await db.flush()

    # 2. Upsert Evidence items for the target scenario
    now_utc = datetime.now(timezone.utc)
    if target_id == NET_SCENARIO_1_ID:
        ev_defs = SCENARIO_MTU_EVIDENCE_DEFINITIONS
    elif target_id == SCENARIO_2_ID:
        ev_defs = SCENARIO_2_EVIDENCE_DEFINITIONS
    elif target_id == SCENARIO_3_ID:
        ev_defs = SCENARIO_3_EVIDENCE_DEFINITIONS
    else:
        ev_defs = DEMO_EVIDENCE_DEFINITIONS

    for item in ev_defs:
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
                incident_id=target_id,
                evidence_type=item["evidence_type"],
                title=item["title"],
                content=item["content"],
                extra_metadata=metadata,
            )
            db.add(new_ev)
        else:
            existing_ev.incident_id = target_id
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
    target_stmt = select(Incident).where(Incident.id == target_id)
    target_res = await db.execute(target_stmt)
    target_incident = target_res.scalars().first()
    return target_incident or inc1


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
        aff_count = 5 if inc.id == SCENARIO_1_ID else (4 if inc.id in (NET_SCENARIO_1_ID, SCENARIO_3_ID) else (3 if inc.id == SCENARIO_2_ID else 1))
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
                affected_services_count=aff_count,
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

    aff_count = 5 if inc.id == SCENARIO_1_ID else (4 if inc.id in (NET_SCENARIO_1_ID, SCENARIO_3_ID) else (3 if inc.id == SCENARIO_2_ID else 1))
    return IncidentSummary(
        id=inc.id,
        title=inc.title,
        description=inc.description,
        status=inc.status.value,
        priority=inc.priority.value,
        category=inc.category.value,
        created_at=inc.created_at,
        evidence_count=ev_count,
        affected_services_count=aff_count,
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
    if incident_id == NET_SCENARIO_1_ID:
        nodes = [
            ServiceNode(
                id="student-portal-ui",
                name="Student Portal UI (Next.js)",
                service_type="frontend",
                status="degraded",
                impact="high",
                metrics_summary={
                    "failure_rate": "84.2%",
                    "p99_latency": "14.2s",
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
                    "http_504_rate": "34.2%",
                    "p99_latency": "14.2s",
                    "tls_handshake_drops": 128,
                },
                supporting_evidence_ids=service_evidence_map.get("portal-gateway", []),
            ),
            ServiceNode(
                id="switch-core-bldg-a",
                name="Core Backbone Switch (switch-core-bldg-a)",
                service_type="switch",
                status="critical",
                impact="root_suspect",
                metrics_summary={
                    "interface": "Te1/0/1",
                    "configured_mtu": "1500 (MISMATCH)",
                    "packet_discards_sec": 380,
                    "jumbo_status": "DISABLED",
                },
                supporting_evidence_ids=service_evidence_map.get("switch-core-bldg-a", []),
            ),
            ServiceNode(
                id="switch-dist-bldg-b",
                name="Distribution Switch (switch-dist-bldg-b)",
                service_type="switch",
                status="warning",
                impact="root_suspect",
                metrics_summary={
                    "interface": "Eth1/1",
                    "configured_mtu": "9216 (Jumbo)",
                    "vlan": "100 (Core Trunk)",
                    "health": "operational",
                },
                supporting_evidence_ids=service_evidence_map.get("switch-dist-bldg-b", []),
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
                target="switch-core-bldg-a",
                relationship="connects_access",
                protocol="10GBASE-T",
                is_degraded=False,
            ),
            ServiceEdge(
                source="switch-core-bldg-a",
                target="switch-dist-bldg-b",
                relationship="inter_switch_trunk",
                protocol="802.1Q/VLAN100 (MTU Mismatch)",
                is_degraded=True,
            ),
            ServiceEdge(
                source="switch-dist-bldg-b",
                target="portal-gateway",
                relationship="routes_gateway",
                protocol="10GBASE-T",
                is_degraded=True,
            ),
            ServiceEdge(
                source="portal-gateway",
                target="campus-ldap-idp",
                relationship="authenticates_request",
                protocol="LDAPS/TCP",
                is_degraded=False,
            ),
        ]
        root_suspects = ["switch-core-bldg-a", "switch-dist-bldg-b"]
        affected_services = ["student-portal-ui", "portal-gateway", "switch-core-bldg-a", "switch-dist-bldg-b"]

    elif incident_id == SCENARIO_2_ID:
        nodes = [
            ServiceNode(
                id="student-portal-ui",
                name="Student Portal UI (Next.js)",
                service_type="frontend",
                status="degraded",
                impact="high",
                metrics_summary={
                    "failure_rate": "92.0%",
                    "client_status": "DHCP_FAILED (APIPA 169.254.x.x)",
                    "wifi_disconnects": 142,
                },
                supporting_evidence_ids=service_evidence_map.get("student-portal-ui", []),
            ),
            ServiceNode(
                id="ap-lib-floor2",
                name="Campus Wi-Fi AP (ap-lib-floor2)",
                service_type="hardware_ap",
                status="critical",
                impact="root_suspect",
                metrics_summary={
                    "active_clients": "128 (Limit: 100)",
                    "channel_utilization": "94.2%",
                    "packet_loss": "24.8%",
                },
                supporting_evidence_ids=service_evidence_map.get("ap-lib-floor2", []),
            ),
            ServiceNode(
                id="gw-border-01",
                name="Border Gateway & DHCP Relay",
                service_type="gateway",
                status="critical",
                impact="root_suspect",
                metrics_summary={
                    "dhcp_leases": "254/254 (0 available)",
                    "subnet": "10.0.4.0/24",
                    "rejected_discovers": 42,
                },
                supporting_evidence_ids=service_evidence_map.get("gw-border-01", []),
            ),
            ServiceNode(
                id="switch-core-bldg-a",
                name="Core Backbone Switch (switch-core-bldg-a)",
                service_type="switch",
                status="healthy",
                impact="none",
                metrics_summary={
                    "crc_errors": 0,
                    "link_state": "10G Full-Duplex",
                    "health": "operational",
                },
                supporting_evidence_ids=service_evidence_map.get("switch-core-bldg-a", []),
            ),
        ]
        edges = [
            ServiceEdge(
                source="student-portal-ui",
                target="ap-lib-floor2",
                relationship="connects_wifi",
                protocol="802.11ax/WPA3",
                is_degraded=True,
            ),
            ServiceEdge(
                source="ap-lib-floor2",
                target="switch-core-bldg-a",
                relationship="uplink_trunk",
                protocol="10GBASE-T",
                is_degraded=True,
            ),
            ServiceEdge(
                source="switch-core-bldg-a",
                target="gw-border-01",
                relationship="dhcp_relay",
                protocol="UDP/67-68",
                is_degraded=True,
            ),
        ]
        root_suspects = ["ap-lib-floor2", "gw-border-01"]
        affected_services = ["student-portal-ui", "ap-lib-floor2", "gw-border-01"]

    elif incident_id == SCENARIO_3_ID:
        nodes = [
            ServiceNode(
                id="student-portal-ui",
                name="Student Portal UI (Next.js)",
                service_type="frontend",
                status="degraded",
                impact="high",
                metrics_summary={
                    "failure_rate": "38.6%",
                    "wan_packet_loss": "31.4%",
                    "p99_latency": "12.8s",
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
                    "http_504_rate": "38.6%",
                    "upstream_timeouts": 164,
                    "wan_dns_latency": "3,200ms",
                },
                supporting_evidence_ids=service_evidence_map.get("portal-gateway", []),
            ),
            ServiceNode(
                id="firewall-edge-01",
                name="Edge Perimeter Firewall (PA-3220)",
                service_type="firewall",
                status="critical",
                impact="root_suspect",
                metrics_summary={
                    "dropped_sessions_min": 4280,
                    "shadowed_rule": "#124 (PERMIT-ACADEMIC)",
                    "shadowing_rule": "#118 (BLOCK-UNREGISTERED)",
                    "status": "POLICY_DRIFT",
                },
                supporting_evidence_ids=service_evidence_map.get("firewall-edge-01", []),
            ),
            ServiceNode(
                id="gw-border-01",
                name="Campus Border Gateway (Cisco ISR 4451)",
                service_type="router",
                status="critical",
                impact="root_suspect",
                metrics_summary={
                    "bgp_peer": "198.51.100.1 (AS1299)",
                    "peer_flaps": "14 in 25 min",
                    "hold_timer": "EXPIRED",
                    "convergence_latency": "48.2s",
                },
                supporting_evidence_ids=service_evidence_map.get("gw-border-01", []),
            ),
            ServiceNode(
                id="switch-core-bldg-a",
                name="Core Backbone Switch (switch-core-bldg-a)",
                service_type="switch",
                status="healthy",
                impact="none",
                metrics_summary={
                    "link_state": "10G Full-Duplex",
                    "crc_errors": 0,
                    "health": "operational",
                },
                supporting_evidence_ids=service_evidence_map.get("switch-core-bldg-a", []),
            ),
        ]
        edges = [
            ServiceEdge(
                source="student-portal-ui",
                target="switch-core-bldg-a",
                relationship="connects_access",
                protocol="10GBASE-T",
                is_degraded=False,
            ),
            ServiceEdge(
                source="switch-core-bldg-a",
                target="portal-gateway",
                relationship="routes_gateway",
                protocol="HTTPS/REST",
                is_degraded=False,
            ),
            ServiceEdge(
                source="portal-gateway",
                target="firewall-edge-01",
                relationship="egress_traffic",
                protocol="TCP/443 (Firewall Drop)",
                is_degraded=True,
            ),
            ServiceEdge(
                source="firewall-edge-01",
                target="gw-border-01",
                relationship="upstream_transit",
                protocol="BGP/IP (Route Flap)",
                is_degraded=True,
            ),
        ]
        root_suspects = ["firewall-edge-01", "gw-border-01"]
        affected_services = ["student-portal-ui", "portal-gateway", "firewall-edge-01", "gw-border-01"]

    else:
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

    if incident_id == SCENARIO_2_ID:
        data_quality_notes = [
            "Access point ap-lib-floor2 telemetry confirms 94.2% RF channel saturation and 128 client associations.",
            "Infoblox DHCP syslog confirms 100% lease exhaustion (254/254) on subnet 10.0.4.0/24.",
            "Student portal logs confirm APIPA 169.254.x.x assignment and gateway unreachability.",
            "Simulated test data generated for TCS Hackathon AIOps Challenge demonstration.",
        ]
    elif incident_id == SCENARIO_3_ID:
        data_quality_notes = [
            "ArgoCD canary rollout v2.4.1 correlated with 64MB Argon2id memory cost surge.",
            "Prometheus cgroup metrics confirm 98.4% CPU utilization and 42.1% CFS throttling.",
            "OpenTelemetry trace spans isolate 8,240ms duration inside auth:argon2_verify span.",
            "Simulated test data generated for TCS Hackathon AIOps Challenge demonstration.",
        ]
    else:
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

