"""Diagnostic Tool Registry for VeriOps Phase 2.

Implements network-first diagnostics and supporting application, database,
infrastructure, and deployment/config inspection tools.
All results are clearly labeled SIMULATED.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from app.schemas.investigation import DiagnosticToolCall


def run_network_connectivity_diagnostic(
    target_service: str = "portal-gateway",
    round_num: int = 1,
) -> DiagnosticToolCall:
    """Primary Network Diagnostic: checks L3/L4 connectivity, DNS, DHCP, gateway, and switch health."""
    simulated_output = {
        "target": target_service,
        "icmp_ping": {
            "packets_transmitted": 10,
            "packets_received": 10,
            "packet_loss_pct": 0.0,
            "avg_latency_ms": 1.24,
            "status": "PASS",
        },
        "dns_resolution": {
            "query": "portal.campusops.edu",
            "record_type": "A",
            "resolved_ip": "10.244.0.15",
            "lookup_duration_ms": 3.8,
            "authoritative_server": "10.0.0.2 (campus-dns-core)",
            "status": "PASS",
        },
        "dhcp_subnets": {
            "client_pool": "10.244.0.0/16",
            "active_leases": 1420,
            "pool_available_pct": 74.2,
            "status": "PASS",
        },
        "gateway_reachability": {
            "port": 443,
            "protocol": "TCP/TLS 1.3",
            "handshake_ms": 4.1,
            "tls_certificate": "Valid (*.campusops.edu, expires in 280 days)",
            "status": "PASS",
        },
        "switch_access_point_health": {
            "core_switch": "switch-core-bldg-a",
            "port": "TenGigabitEthernet 1/0/24",
            "link_speed": "10Gbps Full-Duplex",
            "crc_errors": 0,
            "status": "PASS",
        },
        "downstream_hop_check": {
            "hop_1_gateway_to_auth": {
                "l4_tcp_handshake": "ESTABLISHED (0.8ms)",
                "l7_http_response": "HTTP 504 Gateway Timeout (upstream response timed out after 10000ms)",
            }
        },
        "simulated": True,
    }

    insight = (
        "Network Layer Verification: Campus L3/L4 switching, DNS resolution, DHCP pools, and gateway "
        "TCP connectivity are 100% OPERATIONAL (0% packet loss, 1.2ms latency). The failure is not a "
        "campus network outage, but an application-level upstream timeout originating inside auth-service."
    )

    return DiagnosticToolCall(
        call_id=f"tool-net-{uuid.uuid4().hex[:8]}",
        tool_name="network_connectivity_diagnostic",
        category="network",
        round=round_num,
        target_service=target_service,
        parameters={"targets": [target_service, "campus-dns-core", "switch-core-bldg-a"]},
        simulated_output=simulated_output,
        interpreted_insight=insight,
        executed_at=datetime.now(timezone.utc),
        simulated=True,
    )


def run_application_diagnostics(
    target_service: str = "auth-service",
    round_num: int = 2,
) -> DiagnosticToolCall:
    """Application Diagnostics: checks error logs, exception stack traces, and request timings."""
    simulated_output = {
        "target": target_service,
        "runtime": "Python 3.13 / FastAPI",
        "active_pods": 3,
        "error_log_analysis": {
            "dominant_exception": "sqlalchemy.exc.TimeoutError",
            "error_rate_pct": 84.2,
            "sample_message": "QueuePool limit of size 15 overflow 0 reached, connection timed out, timeout 10.00",
            "stack_trace_top": "app/database.py:35 in get_db -> pool.py:170 in _do_get",
        },
        "distributed_trace_sample": {
            "trace_id": "trace-8891bf40aa91",
            "total_latency_ms": 10214,
            "spans": [
                {"name": "gateway:ingress", "duration_ms": 2},
                {"name": "auth:argon2_verify", "duration_ms": 380},
                {"name": "auth:db_pool_acquisition", "duration_ms": 9820, "status": "TIMEOUT"},
            ],
        },
        "simulated": True,
    }

    insight = (
        "Application Diagnostic: auth-service is spending 9,820ms blocked waiting to acquire an idle "
        "database connection from the async QueuePool. 84.2% of login attempts hit the 10.0s acquisition "
        "timeout and trigger HTTP 504 at the gateway."
    )

    return DiagnosticToolCall(
        call_id=f"tool-app-{uuid.uuid4().hex[:8]}",
        tool_name="application_diagnostics",
        category="application",
        round=round_num,
        target_service=target_service,
        parameters={"service": target_service, "time_window": "15m"},
        simulated_output=simulated_output,
        interpreted_insight=insight,
        executed_at=datetime.now(timezone.utc),
        simulated=True,
    )


def run_database_diagnostics(
    target_service: str = "campusops-db",
    round_num: int = 2,
) -> DiagnosticToolCall:
    """Database Diagnostics: checks connection pool saturation, idle-in-tx locks, and host resources."""
    simulated_output = {
        "target": target_service,
        "engine": "PostgreSQL 15.4 (pgvector)",
        "connection_pool": {
            "current_active_connections": 15,
            "configured_max_connections": 15,
            "utilization_pct": 100.0,
            "wait_queue_length": 48,
        },
        "pg_stat_activity": {
            "total_clients": 15,
            "state_breakdown": {
                "active_executing": 2,
                "idle_in_transaction": 13,
                "idle": 0,
            },
            "oldest_idle_in_tx_seconds": 128,
            "blocking_pid": 4819,
        },
        "system_resources": {
            "cpu_utilization_pct": 14.2,
            "memory_utilization_pct": 42.8,
            "disk_iops_available": 3000,
            "disk_iops_used": 180,
            "status": "HEALTHY",
        },
        "simulated": True,
    }

    insight = (
        "Database Diagnostic: campusops-db host hardware is healthy (14% CPU, plenty of IOPS), but "
        "the active client pool is 100% saturated at 15/15 connections with 48 threads queued. 13 connections "
        "are held in 'idle in transaction' state."
    )

    return DiagnosticToolCall(
        call_id=f"tool-db-{uuid.uuid4().hex[:8]}",
        tool_name="database_diagnostics",
        category="database",
        round=round_num,
        target_service=target_service,
        parameters={"service": target_service, "queries": ["pool_stats", "pg_stat_activity"]},
        simulated_output=simulated_output,
        interpreted_insight=insight,
        executed_at=datetime.now(timezone.utc),
        simulated=True,
    )


def run_deployment_config_diagnostics(
    target_service: str = "auth-service",
    round_num: int = 3,
) -> DiagnosticToolCall:
    """Deployment/Config Diagnostics: checks GitOps commit history and config diffs."""
    simulated_output = {
        "target": target_service,
        "gitops_repo": "campus-ops/helm-deployments",
        "recent_commits": [
            {
                "commit": "a8f912c",
                "author": "infra-bot@campusops.internal",
                "message": "perf: lower idle db pool to 15 to save memory",
                "diff": "- database.pool_size: 50\n+ database.pool_size: 15",
                "deployed_at": "2026-10-31T09:00:00Z",
            },
            {
                "commit": "c4118be",
                "author": "dev-team@campusops.internal",
                "message": "release auth-service v2.4.1 (Argon2id params)",
                "deployed_at": "2026-10-31T09:05:00Z",
            },
        ],
        "config_verification": {
            "current_deployed_pool_size": 15,
            "historical_baseline_pool_size": 50,
            "delta": -35,
        },
        "simulated": True,
    }

    insight = (
        "Configuration Audit: Root cause identified in GitOps commit a8f912c (merged 25 min before incident). "
        "The database pool limit was reduced from 50 to 15. Coupled with v2.4.1's Argon2 memory cost increase "
        "and peak course registration traffic, this triggered total connection pool starvation."
    )

    return DiagnosticToolCall(
        call_id=f"tool-cfg-{uuid.uuid4().hex[:8]}",
        tool_name="deployment_config_diagnostics",
        category="deployment_config",
        round=round_num,
        target_service=target_service,
        parameters={"service": target_service, "commit_depth": 5},
        simulated_output=simulated_output,
        interpreted_insight=insight,
        executed_at=datetime.now(timezone.utc),
        simulated=True,
    )


def run_hardware_device_diagnostics(
    target_service: str = "switch-core-bldg-a",
    round_num: int = 1,
) -> DiagnosticToolCall:
    """Hardware Diagnostics: checks physical network switch and hardware telemetry."""
    simulated_output = {
        "device_id": "switch-core-bldg-a",
        "model": "Cisco Catalyst 9300-48P",
        "status": "OPERATIONAL",
        "fans": "ALL_OK",
        "power_supplies": "DUAL_REDUNDANT_OK",
        "operating_temp_c": 36.4,
        "optical_transceivers": "TX/RX Levels within normal dBm threshold",
        "hardware_faults_detected": False,
        "simulated": True,
    }

    insight = (
        "Hardware Diagnostic: Core switch hardware, optical interfaces, and redundant power supplies "
        "are all operational with 0 hardware faults. No physical maintenance or technician dispatch required."
    )

    return DiagnosticToolCall(
        call_id=f"tool-hw-{uuid.uuid4().hex[:8]}",
        tool_name="hardware_device_diagnostics",
        category="infrastructure",
        round=round_num,
        target_service=target_service,
        parameters={"device": target_service},
        simulated_output=simulated_output,
        interpreted_insight=insight,
        executed_at=datetime.now(timezone.utc),
        simulated=True,
    )

