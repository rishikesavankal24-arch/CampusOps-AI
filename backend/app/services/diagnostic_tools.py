"""Diagnostic Tool Registry for VeriOps Phase 2.

Implements network-first diagnostics and supporting application, database,
infrastructure, and deployment/config inspection tools.
All results are clearly labeled SIMULATED.
"""

from datetime import datetime, timezone
from typing import Any
import uuid

from app.schemas.investigation import DiagnosticToolCall

SCENARIO_1_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
NET_SCENARIO_1_ID = uuid.UUID("44444444-2222-3333-4444-555555555555")
SCENARIO_2_ID = uuid.UUID("22222222-2222-3333-4444-555555555555")
SCENARIO_3_ID = uuid.UUID("33333333-2222-3333-4444-555555555555")


def run_network_connectivity_diagnostic(
    target_service: str = "portal-gateway",
    round_num: int = 1,
    incident_id: uuid.UUID | None = None,
) -> DiagnosticToolCall:
    """Primary Network Diagnostic: checks L3/L4 connectivity, DNS, DHCP, gateway, and switch health."""
    if incident_id == NET_SCENARIO_1_ID:
        simulated_output = {
            "target": "switch-core-bldg-a:Te1/0/1",
            "mtu_sweep_probe": {
                "ping_64b": {"packet_loss_pct": 0.0, "latency_ms": 0.4, "status": "PASS"},
                "ping_1472b": {"packet_loss_pct": 0.0, "latency_ms": 0.6, "status": "PASS"},
                "ping_1500b_df_set": {"packet_loss_pct": 100.0, "latency_ms": None, "status": "FAIL_DF_OVERSIZE"},
                "ping_9000b_jumbo": {"packet_loss_pct": 100.0, "latency_ms": None, "status": "FAIL_DF_OVERSIZE"},
            },
            "interface_mtu_audit": {
                "local_switch": "switch-core-bldg-a",
                "local_interface": "TenGigabitEthernet1/0/1",
                "local_mtu": 1500,
                "remote_switch": "switch-dist-bldg-b",
                "remote_interface": "Ethernet1/1",
                "remote_mtu": 9216,
                "mtu_status": "MISMATCH_DETECTED",
            },
            "trunk_discards": {
                "vlan": 100,
                "discard_rate_sec": 380,
                "cumulative_discards": 18420,
                "crc_errors": 0,
                "physical_carrier": "UP_10G_FULL_DUPLEX",
            },
            "gateway_reachability": {
                "small_payloads": "PASS (< 2ms)",
                "tls_client_cert_payloads": "FAIL_TIMEOUT (> 15000ms)",
                "http_504_rate_pct": 34.2,
            },
            "simulated": True,
        }
        insight = (
            "CRITICAL NETWORK MTU MISMATCH DETECTED: Core switch interface Te1/0/1 is configured for standard MTU 1500 "
            "while peer switch-dist-bldg-b:Eth1/1 uses MTU 9216 Jumbo frames. Frames exceeding 1472 bytes are dropped by "
            "hardware packet policer, causing 100% loss on TLS client certs and cascading HTTP 504 timeouts."
        )

    elif incident_id == SCENARIO_3_ID:
        simulated_output = {
            "target": "gw-border-01 & firewall-edge-01",
            "bgp_peering_status": {
                "primary_peer": "198.51.100.1 (AS1299-Telia-Primary)",
                "primary_state": "ACTIVE / FLAPPING",
                "flaps_last_30m": 14,
                "hold_timer_seconds": 90,
                "last_error": "Hold Timer Expired (BGP Notification 4/0)",
                "secondary_peer": "203.0.113.2 (AS2914-NTT-Secondary)",
                "secondary_state": "ESTABLISHED",
                "secondary_weight": 0,
            },
            "edge_firewall_audit": {
                "firewall": "firewall-edge-01 (PA-3220)",
                "shadowing_rule": "SEC-POLICY-BLOCK-UNREGISTERED (#118)",
                "shadowed_rule": "PERMIT-ACADEMIC-EGRESS (#124)",
                "dropped_sessions_min": 4280,
                "action": "DROP_SECURITY_POLICY_DENY",
                "drift_timestamp": "09:02:00 UTC",
            },
            "wan_egress_probe": {
                "packet_loss_pct": 31.4,
                "dns_8888_latency_ms": 3200,
                "route_convergence_sec": 48.2,
                "status": "CRITICAL_DEGRADATION",
            },
            "simulated": True,
        }
        insight = (
            "CRITICAL BGP FLAPPING & EDGE FIREWALL POLICY SHADOWING DETECTED: Primary BGP peer 198.51.100.1 flapped "
            "14 times in 25 min due to hold-timer expiry, and Edge Firewall rule #118 is shadowing outbound academic transit, "
            "dropping 4,280 sessions/minute."
        )

    elif incident_id == SCENARIO_2_ID:
        simulated_output = {
            "target": "ap-lib-floor2",
            "icmp_ping": {
                "packets_transmitted": 10,
                "packets_received": 7,
                "packet_loss_pct": 24.8,
                "avg_latency_ms": 184.2,
                "status": "FAIL",
            },
            "dns_resolution": {
                "query": "portal.campusops.edu",
                "record_type": "A",
                "resolved_ip": None,
                "lookup_duration_ms": 5000,
                "authoritative_server": "10.0.0.2 (campus-dns-core)",
                "status": "TIMEOUT",
            },
            "dhcp_subnets": {
                "client_pool": "10.0.4.0/24 (Campus Wireless VLAN 104)",
                "total_leases": 254,
                "active_leases": 254,
                "available_leases": 0,
                "pool_available_pct": 0.0,
                "status": "EXHAUSTED",
            },
            "gateway_reachability": {
                "port": 443,
                "protocol": "TCP/TLS 1.3",
                "handshake_ms": 182.4,
                "status": "DEGRADED (Frequent Syn Retransmits)",
            },
            "switch_access_point_health": {
                "access_point": "ap-lib-floor2",
                "location": "Library Floor 2",
                "active_clients": 128,
                "max_rated_clients": 100,
                "channel_utilization_pct": 94.2,
                "snr_db": 12.4,
                "status": "CRITICAL_RF_SATURATION",
            },
            "downstream_hop_check": {
                "hop_1_client_to_ap": {
                    "association_latency_ms": 840,
                    "frame_retry_rate_pct": 38.4,
                    "state": "DEGRADED",
                },
                "hop_2_ap_to_dhcp": {
                    "dhcp_discover_dropped": 42,
                    "state": "NO_LEASES_AVAILABLE",
                },
            },
            "simulated": True,
        }
        insight = (
            "PHYSICAL NETWORK & DHCP EXHAUSTION DETECTED: Access point ap-lib-floor2 is experiencing 24.8% packet loss "
            "and 94.2% RF channel saturation with 128 client associations. DHCP scope 10.0.4.0/24 is 100% exhausted "
            "(0 available leases), rejecting mobile student connections and causing APIPA fallback."
        )
    else:
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
    incident_id: uuid.UUID | None = None,
) -> DiagnosticToolCall:
    """Application Diagnostics: checks error logs, exception stack traces, and request timings."""
    if incident_id == SCENARIO_3_ID:
        simulated_output = {
            "target": target_service,
            "runtime": "Python 3.13 / FastAPI (auth-service:v2.4.1 canary)",
            "active_pods": 3,
            "cpu_utilization_pct": 98.4,
            "cfs_throttled_periods_pct": 42.1,
            "error_log_analysis": {
                "dominant_exception": "asyncio.exceptions.TimeoutError",
                "error_rate_pct": 41.2,
                "sample_message": "Upstream timeout waiting for argon2_verify CPU worker execution (threshold: 8000ms)",
                "stack_trace_top": "app/auth/security.py:42 in verify_password -> argon2.low_level.verify_secret",
            },
            "distributed_trace_sample": {
                "trace_id": "trace-argon2-thrash-0915",
                "total_latency_ms": 10120,
                "spans": [
                    {"name": "gateway:ingress", "duration_ms": 3},
                    {"name": "auth:argon2_verify", "duration_ms": 8240, "status": "THROTTLED"},
                    {"name": "auth:db_pool_acquisition", "duration_ms": 14, "status": "OK"},
                ],
            },
            "simulated": True,
        }
        insight = (
            "Application Diagnostic: auth-service pod CPU is pegged at 98.4% with 42.1% cgroup CFS throttling. "
            "Trace analysis proves argon2_verify is taking 8,240ms per verification (baseline: 320ms) due to the 64MB "
            "memory cost increase, exhausting worker threads and tripping gateway timeouts."
        )
    else:
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
    incident_id: uuid.UUID | None = None,
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
    incident_id: uuid.UUID | None = None,
) -> DiagnosticToolCall:
    """Deployment/Config Diagnostics: checks GitOps commit history and config diffs."""
    if incident_id == SCENARIO_3_ID:
        simulated_output = {
            "target": target_service,
            "gitops_repo": "campus-ops/helm-deployments",
            "recent_commits": [
                {
                    "commit": "d981a2f",
                    "author": "security-team@campusops.internal",
                    "message": "security: strengthen Argon2id hash memory cost to 64MB",
                    "diff": "- security.argon2.memory_cost: 16384\n+ security.argon2.memory_cost: 65536",
                    "deployed_at": "2026-10-31T09:04:00Z",
                },
                {
                    "commit": "a149c81",
                    "author": "release-bot@campusops.internal",
                    "message": "promote auth-service:v2.4.1 canary to 10% traffic",
                    "diff": "+ canary.traffic_weight: 10",
                    "deployed_at": "2026-10-31T09:02:00Z",
                },
            ],
            "config_verification": {
                "current_argon2_memory_cost_kb": 65536,
                "historical_baseline_kb": 16384,
                "current_cpu_utilization_pct": 98.4,
            },
            "simulated": True,
        }
        insight = (
            "Configuration Audit: Root cause identified in GitOps commit d981a2f (canary v2.4.1). "
            "Argon2id memory_cost was quadrupled from 16MB to 64MB per hash. Under concurrent student login load, "
            "this exhausted CPU worker threads and triggered 98.4% CPU saturation with 42.1% CFS throttling."
        )
    else:
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

