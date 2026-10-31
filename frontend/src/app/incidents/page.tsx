"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  IncidentSummary,
  IncidentTimelineResponse,
  ServiceDependencyGraphResponse,
  EvidenceBundleResponse,
  NormalizedEvidenceItem,
} from "@/types/incident";
import {
  InvestigationStateResponse,
  InvestigationTrackerResponse,
  HardwareDeviceImpact,
} from "@/types/investigation";
import NexoraDashboardView from "@/components/dashboard/NexoraDashboardView";
import LifecycleWorkflowDiagram from "@/components/incidents/LifecycleWorkflowDiagram";
import ServiceGraph from "@/components/incidents/ServiceGraph";
import IncidentTimeline from "@/components/incidents/IncidentTimeline";
import InvestigationPanel from "@/components/incidents/InvestigationPanel";
import InvestigationTracker from "@/components/incidents/InvestigationTracker";
import EvidenceDetailModal from "@/components/incidents/EvidenceDetailModal";
import EvidenceBundleModal from "@/components/incidents/EvidenceBundleModal";
import {
  LayoutDashboard,
  Flame,
  Bot,
  Network,
  Clock,
  CheckCircle2,
  Activity,
  ChevronLeft,
  ChevronRight,
  Search,
  PlayCircle,
  PackageCheck,
  AlertTriangle,
  UserCheck,
  Server,
  ShieldCheck,
  LogOut,
  GitBranch,
  ListOrdered,
  ArrowRight,
} from "lucide-react";

const DEMO_INCIDENT_ID = "44444444-2222-3333-4444-555555555555";

export const DEMO_SCENARIOS = [
  {
    id: "44444444-2222-3333-4444-555555555555",
    label: "Scenario 1: Campus Core Switch Trunk MTU Mismatch & Frame Drops",
    shortLabel: "Scenario 1 (Core Switch MTU)",
    badge: "CORE SWITCHING",
    badgeColor: "bg-cyan-950 text-cyan-300 border-cyan-800",
  },
  {
    id: "22222222-2222-3333-4444-555555555555",
    label: "Scenario 2: Campus Wi-Fi Degradation & DHCP Scope Exhaustion",
    shortLabel: "Scenario 2 (Wi-Fi / DHCP)",
    badge: "WIRELESS & DHCP",
    badgeColor: "bg-rose-950 text-rose-300 border-rose-800",
  },
  {
    id: "33333333-2222-3333-4444-555555555555",
    label: "Scenario 3: Border Gateway BGP Flapping & Edge Firewall Drift",
    shortLabel: "Scenario 3 (WAN BGP / Firewall)",
    badge: "WAN & FIREWALL",
    badgeColor: "bg-amber-950 text-amber-300 border-amber-800",
  },
];

export type NavigationTab =
  | "overview"
  | "incidents"
  | "investigation"
  | "topology"
  | "evidence"
  | "recovery"
  | "tracker";

function IncidentsWorkspaceContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading, logout } = useAuth();

  // Navigation tab state (defaults to 'overview')
  const initialTab = (searchParams.get("tab") as NavigationTab) || "overview";
  const [activeTab, setActiveTab] = useState<NavigationTab>(initialTab);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");

  // Incident selection state
  const [allIncidents, setAllIncidents] = useState<IncidentSummary[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>(DEMO_INCIDENT_ID);

  // Data states for the active incident
  const [incident, setIncident] = useState<IncidentSummary | null>(null);
  const [timeline, setTimeline] = useState<IncidentTimelineResponse | null>(null);
  const [graph, setGraph] = useState<ServiceDependencyGraphResponse | null>(null);
  const [bundle, setBundle] = useState<EvidenceBundleResponse | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationStateResponse | null>(null);
  const [tracker, setTracker] = useState<InvestigationTrackerResponse | null>(null);

  // Status & modal states
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);

  // Recovery confirmation modal in Recovery Tab
  const [showRecoveryConfirm, setShowRecoveryConfirm] = useState(false);
  const [pendingForceFailure, setPendingForceFailure] = useState(false);
  const [operatorNotes, setOperatorNotes] = useState("Authorized remediation following SRE runbook.");

  // Timeline filters
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [selectedSourceType, setSelectedSourceType] = useState<string | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null);

  // Modals
  const [inspectingEvidence, setInspectingEvidence] = useState<NormalizedEvidenceItem | null>(null);
  const [showBundleModal, setShowBundleModal] = useState(false);

  // Sync tab with URL query parameter
  const handleTabChange = (tab: NavigationTab) => {
    setActiveTab(tab);
    window.history.replaceState(null, "", `/incidents?tab=${tab}`);
  };

  // Auth guard
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login?from=/incidents");
    }
  }, [user, authLoading, router]);

  // Unified non-cascading data loader
  useEffect(() => {
    if (!user) return;
    let isCancelled = false;

    async function fetchData() {
      try {
        setError(null);
        const targetId = selectedIncidentId || DEMO_INCIDENT_ID;

        // 1. Fetch all incidents list for switcher & queue
        try {
          const listRes = await fetch("/api/incidents");
          if (listRes.ok && !isCancelled) {
            const list: IncidentSummary[] = await listRes.json();
            setAllIncidents(list);
          }
        } catch {
          // Ignore listing error
        }

        // 2. Fetch incident summary or auto-seed if demo missing
        let incRes = await fetch(`/api/incidents/${targetId}`);
        if (incRes.status === 404 && targetId === DEMO_INCIDENT_ID) {
          const seedRes = await fetch("/api/incidents", { method: "POST" });
          if (!seedRes.ok) {
            throw new Error("Failed to initialize demo incident.");
          }
          incRes = await fetch(`/api/incidents/${DEMO_INCIDENT_ID}`);
        }

        if (!incRes.ok) {
          throw new Error("Unable to retrieve incident records.");
        }
        const incData: IncidentSummary = await incRes.json();

        // Fetch Dependency Graph
        const graphRes = await fetch(`/api/incidents/${targetId}/graph`);
        const graphData: ServiceDependencyGraphResponse | null = graphRes.ok
          ? await graphRes.json()
          : null;

        // Fetch Timeline with filters
        const params = new URLSearchParams();
        if (selectedSourceType) params.set("source_type", selectedSourceType);
        if (selectedSeverity) params.set("severity", selectedSeverity);
        if (selectedService) params.set("service_name", selectedService);

        const qs = params.toString();
        const timelineRes = await fetch(
          `/api/incidents/${targetId}/timeline${qs ? `?${qs}` : ""}`
        );
        const timelineData: IncidentTimelineResponse | null = timelineRes.ok
          ? await timelineRes.json()
          : null;

        // Fetch Evidence Bundle Manifest
        const bundleRes = await fetch(`/api/incidents/${targetId}/bundle`);
        const bundleData: EvidenceBundleResponse | null = bundleRes.ok
          ? await bundleRes.json()
          : null;

        // Fetch Active Investigation State
        const invRes = await fetch(`/api/incidents/${targetId}/investigation`);
        const invData: InvestigationStateResponse | null = invRes.ok
          ? await invRes.json()
          : null;

        // Fetch Persistent 13-Stage Investigation Tracker
        const trackerRes = await fetch(`/api/incidents/${targetId}/investigation/tracker`);
        const trackerData: InvestigationTrackerResponse | null = trackerRes.ok
          ? await trackerRes.json()
          : null;

        if (!isCancelled) {
          setIncident(incData);
          if (graphData) setGraph(graphData);
          if (timelineData) setTimeline(timelineData);
          if (bundleData) setBundle(bundleData);
          if (invData) setInvestigation(invData);
          if (trackerData) setTracker(trackerData);
          setLoading(false);
        }
      } catch (err: unknown) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : "Error loading incident workspace");
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      isCancelled = true;
    };
  }, [user, selectedIncidentId, selectedService, selectedSourceType, selectedSeverity, refreshCount]);

  // Refresh Tracker helper
  const refreshTracker = async () => {
    try {
      const res = await fetch(`/api/incidents/${selectedIncidentId}/investigation/tracker`);
      if (res.ok) setTracker(await res.json());
    } catch {
      // Ignore background refresh errors
    }
  };

  // Investigation action handlers
  const handleRunDiagnostic = async (toolName?: string) => {
    try {
      const res = await fetch(`/api/incidents/${selectedIncidentId}/investigation/diagnose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool_name: toolName }),
      });
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(updated);
        await refreshTracker();
        setRefreshCount((prev) => prev + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Diagnostic execution failed");
    }
  };

  const handleApprove = async (decision: "approve" | "reject", notes?: string) => {
    try {
      const res = await fetch(`/api/incidents/${selectedIncidentId}/investigation/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, notes: notes || operatorNotes }),
      });
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(updated);
        await refreshTracker();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval request failed");
    }
  };

  const handleConfirmRecoveryExecution = async () => {
    setShowRecoveryConfirm(false);
    try {
      const res = await fetch(
        `/api/incidents/${selectedIncidentId}/investigation/execute-recovery`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ force_verification_failure: pendingForceFailure }),
        }
      );
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(updated);
        await refreshTracker();
        setRefreshCount((prev) => prev + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Recovery execution failed");
    }
  };

  const handleTriggerRecoveryPrompt = async (forceFailure: boolean) => {
    setPendingForceFailure(forceFailure);
    setShowRecoveryConfirm(true);
  };

  const handleResetInvestigation = async () => {
    try {
      const res = await fetch(`/api/incidents/${selectedIncidentId}/investigation/reset`, {
        method: "POST",
      });
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(updated);
        await refreshTracker();
        setRefreshCount((prev) => prev + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    }
  };

  const handleEscalate = async () => {
    try {
      const res = await fetch(`/api/incidents/${selectedIncidentId}/investigation/escalate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "SRE operator requested manual Tier-3 escalation" }),
      });
      if (res.ok) {
        const updated = await res.json();
        setInvestigation(updated);
        await refreshTracker();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Escalation failed");
    }
  };

  // Re-seed demo telemetry and reset investigation state
  const handleResetDemo = async (scenarioId?: string) => {
    try {
      setSeeding(true);
      setError(null);
      const targetId = scenarioId || selectedIncidentId || DEMO_INCIDENT_ID;

      // 1. Re-seed incident & evidence
      const res = await fetch(`/api/incidents?scenario_id=${encodeURIComponent(targetId)}`, {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Reset failed.");
      }

      // 2. Explicitly call reset on the investigation orchestrator to return to fresh initial state
      const invResetRes = await fetch(`/api/incidents/${targetId}/investigation/reset`, {
        method: "POST",
      });
      if (invResetRes.ok) {
        const freshInv = await invResetRes.json();
        setInvestigation(freshInv);
      }

      // 3. Refresh tracker & incident summary
      const trackerRes = await fetch(`/api/incidents/${targetId}/investigation/tracker`);
      if (trackerRes.ok) {
        setTracker(await trackerRes.json());
      }
      const incRes = await fetch(`/api/incidents/${targetId}`);
      if (incRes.ok) {
        setIncident(await incRes.json());
      }

      setSelectedIncidentId(targetId);

      // 4. Refetch incidents list
      const listRes = await fetch("/api/incidents");
      if (listRes.ok) {
        const listData = await listRes.json();
        setAllIncidents(listData);
      }

      setRefreshCount((prev) => prev + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset demo dataset");
    } finally {
      setSeeding(false);
    }
  };

  // Filtered timeline events
  const filteredTimelineEvents = useMemo(() => {
    if (!timeline) return [];
    if (!globalSearch.trim()) return timeline.events;
    const q = globalSearch.toLowerCase();
    return timeline.events.filter(
      (e) =>
        e.title.toLowerCase().includes(q) ||
        e.content.toLowerCase().includes(q) ||
        e.service_name.toLowerCase().includes(q) ||
        e.source_type.toLowerCase().includes(q)
    );
  }, [timeline, globalSearch]);

  if (authLoading || (!user && loading)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0b132b] text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin" />
          <p className="text-xs text-sky-400 font-mono">
            Connecting to VeriOps Operations Center...
          </p>
        </div>
      </div>
    );
  }

  // 7 Operations Navigation Items + 1 AI Assistant Item
  const operationsNavItems = [
    {
      id: "overview" as NavigationTab,
      label: "Overview",
      icon: LayoutDashboard,
      badge: "Live",
      badgeColor: "bg-sky-500/10 text-sky-300 border-sky-500/30",
    },
    {
      id: "incidents" as NavigationTab,
      label: "Incidents",
      icon: ListOrdered,
      badge: `${allIncidents.length || 1}`,
      badgeColor: "bg-rose-500/10 text-rose-300 border-rose-500/30",
    },
    {
      id: "investigation" as NavigationTab,
      label: "Investigation",
      icon: GitBranch,
      badge: investigation?.current_stage || "Active",
      badgeColor: "bg-blue-500/10 text-blue-300 border-blue-500/30",
    },
    {
      id: "topology" as NavigationTab,
      label: "Network Topology",
      icon: Network,
      badge: "4 Devices",
      badgeColor: "bg-sky-500/10 text-sky-300 border-sky-500/30",
    },
    {
      id: "evidence" as NavigationTab,
      label: "Evidence & Timeline",
      icon: Clock,
      badge: `${timeline?.filtered_events || 11}`,
      badgeColor: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    },
    {
      id: "recovery" as NavigationTab,
      label: "Recovery & Verification",
      icon: CheckCircle2,
      badge: investigation?.verification_result?.verified ? "Passed" : "Action",
      badgeColor: investigation?.verification_result?.verified
        ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/30"
        : "bg-amber-500/10 text-amber-300 border-amber-500/30",
    },
    {
      id: "tracker" as NavigationTab,
      label: "Investigation Tracker",
      icon: Activity,
      badge: "13 Stages",
      badgeColor: "bg-slate-700/40 text-slate-300 border-slate-600/40",
    },
  ];

  return (
    <div className="min-h-screen bg-[#0b132b] text-slate-100 flex flex-row font-sans selection:bg-sky-500/30">
      {/* =========================================================================
          LEFT SIDEBAR: Operations Control Center
          ========================================================================= */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 bg-[#0d1527] border-r border-[#1e2e54] flex flex-col transition-all duration-300 ease-in-out ${
          sidebarCollapsed ? "w-20" : "w-64"
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-4 border-b border-[#1e2e54] flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-xl bg-[#182344] border border-[#1e2e54] flex items-center justify-center flex-shrink-0 shadow-md">
              <Flame className="w-5 h-5 text-sky-400" />
            </div>
            {!sidebarCollapsed && (
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="font-bold text-base text-white tracking-tight">VeriOps</span>
                  <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-[#182344] text-sky-300 border border-[#1e2e54]">
                    TCS
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 font-medium truncate">
                  Operations Console
                </span>
              </div>
            )}
          </div>

          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="text-slate-400 hover:text-sky-300 p-1.5 rounded-lg hover:bg-[#182344] transition-colors cursor-pointer"
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Sidebar Navigation */}
        <div className="flex-1 py-4 px-2 space-y-6 overflow-y-auto">
          {/* Group 1: Operations */}
          <div>
            {!sidebarCollapsed && (
              <div className="px-3 pb-2 text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                Operations
              </div>
            )}
            <div className="space-y-1">
              {operationsNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => handleTabChange(item.id)}
                    title={sidebarCollapsed ? item.label : undefined}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium transition-all cursor-pointer ${
                      isActive
                        ? "bg-[#182344] text-sky-200 border-l-2 border-sky-400 font-semibold shadow-sm"
                        : "text-slate-400 hover:text-slate-200 hover:bg-[#131d38]"
                    }`}
                  >
                    <Icon
                      className={`w-4 h-4 flex-shrink-0 ${
                        isActive ? "text-sky-400" : "text-slate-400"
                      }`}
                    />
                    {!sidebarCollapsed && (
                      <div className="flex items-center justify-between w-full">
                        <span className="truncate">{item.label}</span>
                        {item.badge && (
                          <span
                            className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${item.badgeColor}`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Group 2: AI Assistant */}
          <div>
            {!sidebarCollapsed && (
              <div className="px-3 pb-2 text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                AI Assistant
              </div>
            )}
            <Link
              href="/chat"
              title={sidebarCollapsed ? "Chat / RAG" : undefined}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-sky-200 hover:bg-[#131d38] transition-all"
            >
              <Bot className="w-4 h-4 text-sky-400 flex-shrink-0" />
              {!sidebarCollapsed && (
                <div className="flex items-center justify-between w-full">
                  <span>Chat / RAG</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#182344] text-sky-300 border border-[#1e2e54]">
                    KB
                  </span>
                </div>
              )}
            </Link>
          </div>
        </div>

        {/* Sidebar Footer: User Profile & Session */}
        <div className="p-3 border-t border-[#1e2e54] bg-[#0b132b]">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-[#182344] border border-[#1e2e54] flex items-center justify-center flex-shrink-0 text-sky-300 font-bold text-xs">
                {user?.name ? user.name[0].toUpperCase() : "U"}
              </div>
              {!sidebarCollapsed && (
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-200 truncate">
                    {user?.name || "SRE Operator"}
                  </p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[10px] font-mono uppercase text-slate-400 truncate">
                      {user?.role || "Support"}
                    </span>
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => logout()}
              title="Logout"
              className="text-slate-400 hover:text-rose-400 p-1.5 rounded-lg hover:bg-rose-950/30 transition-colors cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* =========================================================================
          MAIN APPLICATION SHELL: Header + Content
          ========================================================================= */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          sidebarCollapsed ? "ml-20" : "ml-64"
        }`}
      >
        {/* Top Header Bar with Dynamic Incident Switcher */}
        <header className="h-16 border-b border-[#1e2e54] bg-[#0d1527] sticky top-0 z-30 px-6 flex items-center justify-between gap-4">
          {/* Dynamic Incident Switcher Dropdown */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-[#131d38] border border-[#1e2e54] px-2.5 py-1.5 rounded-lg text-xs">
              <Flame className="w-3.5 h-3.5 text-rose-400 shrink-0" />
              <select
                value={selectedIncidentId}
                onChange={(e) => setSelectedIncidentId(e.target.value)}
                className="bg-transparent text-slate-200 font-mono font-medium text-xs focus:outline-none cursor-pointer max-w-[280px] truncate"
                title="Switch active incident"
              >
                {allIncidents.length > 0 ? (
                  allIncidents.map((inc) => (
                    <option key={inc.id} value={inc.id} className="bg-[#0d1527] text-slate-200">
                      {inc.title}
                    </option>
                  ))
                ) : (
                  <option value={DEMO_INCIDENT_ID} className="bg-[#0d1527] text-slate-200">
                    INC-2026-001 • Core Switch Trunk MTU Mismatch
                  </option>
                )}
              </select>

              <span
                className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border font-bold ${
                  incident?.status === "resolved"
                    ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                    : "bg-rose-950 text-rose-300 border-rose-800"
                }`}
              >
                {incident?.status === "resolved" ? "RESOLVED" : "P1 CRITICAL"}
              </span>
            </div>
          </div>

          {/* Search Box & Context Tag */}
          <div className="flex items-center flex-1 max-w-md mx-2 gap-2">
            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search telemetry, traces, services..."
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                className="w-full bg-[#131d38] border border-[#1e2e54] focus:border-sky-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none transition font-mono"
              />
              {globalSearch && (
                <button
                  onClick={() => setGlobalSearch("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-[10px] cursor-pointer"
                >
                  Clear
                </button>
              )}
            </div>

            <span className="hidden xl:flex items-center gap-1.5 text-[10px] font-mono px-2 py-1 rounded bg-amber-950/60 text-amber-300 border border-amber-800/60 shrink-0">
              <AlertTriangle className="w-3 h-3 text-amber-400" />
              SIMULATED SRE
            </span>
          </div>

          {/* Action Controls */}
          <div className="flex items-center gap-2">
            {/* Scenario Selector Dropdown */}
            <div className="flex items-center gap-1.5 bg-[#131d38] border border-[#1e2e54] rounded-lg px-2.5 py-1 text-xs">
              <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 font-semibold hidden md:inline">
                Scenario:
              </span>
              <select
                value={selectedIncidentId}
                onChange={(e) => {
                  const newId = e.target.value;
                  setSelectedIncidentId(newId);
                  handleResetDemo(newId);
                }}
                disabled={seeding}
                className="bg-transparent text-sky-300 font-medium text-xs border-0 outline-none cursor-pointer focus:ring-0"
              >
                {DEMO_SCENARIOS.map((sc) => (
                  <option key={sc.id} value={sc.id} className="bg-[#0b132b] text-slate-200">
                    {sc.shortLabel}
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={() => handleResetDemo(selectedIncidentId)}
              disabled={seeding}
              className="text-xs px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-slate-950 font-bold border border-sky-400 flex items-center gap-1.5 transition-all shadow-md disabled:opacity-50 cursor-pointer"
              title="Re-seed telemetry for active scenario"
            >
              <PlayCircle className="w-3.5 h-3.5 text-slate-950" />
              <span>{seeding ? "Re-seeding..." : "Trigger Scenario"}</span>
            </button>

            <button
              onClick={() => setShowBundleModal(true)}
              className="hidden sm:flex text-xs px-2.5 py-1.5 rounded-lg bg-[#131d38] hover:bg-[#182344] text-sky-300 border border-[#1e2e54] items-center gap-1.5 transition cursor-pointer"
              title="Inspect verifiable evidence bundle JSON"
            >
              <PackageCheck className="w-3.5 h-3.5 text-sky-400" />
              <span className="font-mono text-[11px]">Bundle JSON</span>
            </button>
          </div>
        </header>

        {/* =========================================================================
            WORKSPACE CONTENT TABS
            ========================================================================= */}
        <main className="flex-1 p-6 space-y-6">
          {error && (
            <div className="p-3 rounded-xl bg-rose-950/80 border border-rose-800 text-rose-300 text-xs font-mono flex items-center justify-between">
              <span>
                <strong>System Error:</strong> {error}
              </span>
              <button
                onClick={() => setError(null)}
                className="text-rose-400 hover:text-white text-xs underline cursor-pointer"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* TAB 1: OVERVIEW */}
          {activeTab === "overview" && (
            <NexoraDashboardView
              incident={incident}
              allIncidents={allIncidents}
              timeline={timeline}
              graph={graph}
              investigation={investigation}
              tracker={tracker}
              onNavigateToTab={(tab) => handleTabChange(tab as NavigationTab)}
              onSelectIncident={(id) => {
                setSelectedIncidentId(id);
                setRefreshCount((prev) => prev + 1);
              }}
              onTriggerDemo={handleResetDemo}
              onRunNextDiagnostic={handleRunDiagnostic}
            />
          )}

          {/* TAB 2: INCIDENTS QUEUE TABLE */}
          {activeTab === "incidents" && (
            <div className="space-y-4 animate-fadeIn">
              <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 shadow-lg">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-[#1e2e54]">
                  <div>
                    <h2 className="text-base font-bold text-white flex items-center gap-2">
                      <ListOrdered className="w-5 h-5 text-sky-400" />
                      Incident Operations Queue
                    </h2>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Active and historical production incidents under automated investigation
                    </p>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="px-2 py-0.5 rounded bg-[#0b132b] text-sky-300 border border-[#1e2e54]">
                      Total: {allIncidents.length || 1}
                    </span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-[#0b132b] text-[11px] font-mono text-sky-400 uppercase border-b border-[#1e2e54]">
                      <tr>
                        <th className="px-4 py-3">Incident ID</th>
                        <th className="px-4 py-3">Title & Hypothesis</th>
                        <th className="px-4 py-3">Service</th>
                        <th className="px-4 py-3">Severity</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Created</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1e2e54]">
                      {(allIncidents.length > 0 ? allIncidents : [incident]).filter(Boolean).map((inc) => {
                        const isCurrent = inc?.id === selectedIncidentId;
                        return (
                          <tr
                            key={inc?.id}
                            className={`hover:bg-[#182344]/50 transition-colors font-mono ${
                              isCurrent ? "bg-[#182344]/30" : ""
                            }`}
                          >
                            <td className="px-4 py-3.5 font-bold text-slate-200">
                              <span className="text-sky-300">{inc?.id ? inc.id.slice(0, 8) : "INC-001"}...</span>
                            </td>
                            <td className="px-4 py-3.5 font-sans">
                              <div className="font-semibold text-white">{inc?.title}</div>
                              <div className="text-[11px] text-slate-400 font-mono truncate max-w-sm">
                                {inc?.description || "Automated hypothesis correlation in progress"}
                              </div>
                            </td>
                            <td className="px-4 py-3.5 text-slate-300">{inc?.category || "Infrastructure"}</td>
                            <td className="px-4 py-3.5">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-300 border border-rose-800">
                                {inc?.priority?.toUpperCase() || "CRITICAL"}
                              </span>
                            </td>
                            <td className="px-4 py-3.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                                  inc?.status === "resolved"
                                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                                    : "bg-amber-950 text-amber-300 border-amber-800"
                                }`}
                              >
                                {inc?.status?.toUpperCase() || "INVESTIGATING"}
                              </span>
                            </td>
                            <td className="px-4 py-3.5 text-slate-400 text-[11px]">
                              {inc?.created_at ? new Date(inc.created_at).toLocaleTimeString() : "Just now"}
                            </td>
                            <td className="px-4 py-3.5 text-right">
                              <button
                                onClick={() => {
                                  if (inc?.id) {
                                    setSelectedIncidentId(inc.id);
                                    handleTabChange("investigation");
                                  }
                                }}
                                className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1 ml-auto cursor-pointer transition ${
                                  isCurrent
                                    ? "bg-sky-600 hover:bg-sky-500 text-slate-950"
                                    : "bg-[#0b132b] hover:bg-[#1e2e54] text-slate-200 border border-[#1e2e54]"
                                }`}
                              >
                                <span>{isCurrent ? "Active" : "Select"}</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: INVESTIGATION */}
          {activeTab === "investigation" && (
            <div className="space-y-6 animate-fadeIn">
              <LifecycleWorkflowDiagram
                investigation={investigation}
                tracker={tracker}
                onInspectEvidenceId={(id) => {
                  const ev = timeline?.events.find((e) => String(e.evidence_id) === id);
                  if (ev) setInspectingEvidence(ev);
                }}
                onEscalate={handleEscalate}
                onTriggerReinvestigate={handleResetInvestigation}
              />

              {investigation && (
                <InvestigationPanel
                  state={investigation}
                  onRunDiagnostic={handleRunDiagnostic}
                  onApprove={handleApprove}
                  onExecuteRecovery={handleTriggerRecoveryPrompt}
                  onReset={handleResetInvestigation}
                />
              )}
            </div>
          )}

          {/* TAB 4: NETWORK TOPOLOGY */}
          {activeTab === "topology" && (
            <div className="space-y-6 animate-fadeIn">
              {graph && (
                <ServiceGraph
                  graph={graph}
                  selectedService={selectedService}
                  onSelectService={setSelectedService}
                />
              )}

              {/* Physical Hardware Digital Twin */}
              <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Server className="w-4 h-4 text-sky-400" />
                    Physical Infrastructure & Network Device Health
                  </h3>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0b132b] text-sky-300 border border-[#1e2e54]">
                    Connected Hardware
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5">
                  {(
                    tracker?.device_mapping || [
                      {
                        device_name: "switch-core-bldg-a",
                        device_type: "switch",
                        ip_address: "10.0.1.1",
                        location: "Datacenter Rack 2",
                        status: "HEALTHY",
                        health_summary: { packet_loss_pct: 0.0, crc_errors: 0 },
                        impacted_services: ["campus-api-gateway", "identity-service"],
                        technician_recommendation: "L2/L3 switching verified normal.",
                        simulated: true,
                      },
                      {
                        device_name: "gw-border-01",
                        device_type: "gateway",
                        ip_address: "10.0.0.1",
                        location: "Border DMZ",
                        status: "HEALTHY",
                        health_summary: { packet_loss_pct: 0.0, bgp_state: "ESTABLISHED" },
                        impacted_services: ["campus-api-gateway"],
                        technician_recommendation: "Border routing normal; peering active.",
                        simulated: true,
                      },
                      {
                        device_name: "ap-lib-floor2",
                        device_type: "access_point",
                        ip_address: "10.0.4.15",
                        location: "Library 2nd Floor",
                        status: "HEALTHY",
                        health_summary: { active_clients: 42, channel_utilization_pct: 32 },
                        impacted_services: ["student-portal-ui"],
                        technician_recommendation: "Wi-Fi RF clean; auth packets forwarded.",
                        simulated: true,
                      },
                      {
                        device_name: "dns-campus-primary",
                        device_type: "dns_resolver",
                        ip_address: "10.0.0.53",
                        location: "Network Ops Center",
                        status: "HEALTHY",
                        health_summary: { query_latency_ms: 1.2, cache_hit_pct: 94.8 },
                        impacted_services: ["campus-api-gateway", "identity-service"],
                        technician_recommendation: "DNS resolution verified at 1.2ms.",
                        simulated: true,
                      },
                    ]
                  ).map((dev: HardwareDeviceImpact) => (
                    <div
                      key={dev.device_name}
                      className="bg-[#0b132b] border border-[#1e2e54] rounded-xl p-3.5 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center justify-between text-xs mb-2">
                          <span className="font-mono font-bold text-slate-200">
                            {dev.device_name}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                            {dev.status}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 space-y-1 mb-3 font-mono">
                          <p>Type: {dev.device_type}</p>
                          <p>IP: {dev.ip_address}</p>
                          <p className="truncate">Loc: {dev.location}</p>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-[#1e2e54] text-[10px] text-slate-400 font-mono">
                        <span className="text-sky-400 font-semibold block mb-0.5">
                          Downstream Services:
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {dev.impacted_services.map((svc) => (
                            <span
                              key={svc}
                              className="px-1.5 py-0.2 rounded bg-[#131d38] text-sky-300 border border-[#1e2e54]"
                            >
                              {svc}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: EVIDENCE & TIMELINE */}
          {activeTab === "evidence" && timeline && (
            <div className="space-y-6 animate-fadeIn">
              <IncidentTimeline
                events={filteredTimelineEvents}
                selectedSourceType={selectedSourceType}
                selectedSeverity={selectedSeverity}
                onSelectSourceType={setSelectedSourceType}
                onSelectSeverity={setSelectedSeverity}
                onInspectEvidence={setInspectingEvidence}
              />
            </div>
          )}

          {/* TAB 6: RECOVERY & VERIFICATION */}
          {activeTab === "recovery" && (
            <div className="space-y-6 animate-fadeIn">
              {investigation ? (
                <>
                  <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-6 shadow-xl">
                    <div className="flex items-center justify-between pb-4 border-b border-[#1e2e54]">
                      <div>
                        <h2 className="text-base font-bold text-white flex items-center gap-2">
                          <CheckCircle2 className="w-5 h-5 text-sky-400" />
                          Remediation Plan & Human Gate
                        </h2>
                        <p className="text-xs text-slate-400 mt-0.5">
                          Autonomous mitigation with mandatory operator authorization
                        </p>
                      </div>
                      <span
                        className={`text-xs font-mono uppercase px-2.5 py-1 rounded border font-bold ${
                          investigation.current_stage === "RESOLVED"
                            ? "bg-emerald-950 text-emerald-300 border-emerald-600"
                            : investigation.current_stage === "AWAITING_APPROVAL"
                            ? "bg-amber-950 text-amber-300 border-amber-600 animate-pulse"
                            : "bg-[#182344] text-sky-300 border-[#1e2e54]"
                        }`}
                      >
                        Stage: {investigation.current_stage}
                      </span>
                    </div>

                    {investigation.recovery_plan ? (
                      <div className="mt-5 space-y-4">
                        <div className="bg-[#0b132b] p-4 rounded-xl border border-[#1e2e54] space-y-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-mono text-xs font-bold text-sky-300">
                              {investigation.recovery_plan.action_id}:{" "}
                              {investigation.recovery_plan.action_name}
                            </span>
                            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                              Risk: {investigation.recovery_plan.risk_level}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 text-xs font-mono">
                            <div className="bg-[#182344] p-2.5 rounded border border-[#1e2e54] text-slate-300">
                              <span className="text-[10px] text-sky-400 block mb-1">
                                Expected Signal:
                              </span>
                              {investigation.recovery_plan.expected_signal}
                            </div>
                            <div className="bg-[#182344] p-2.5 rounded border border-[#1e2e54] text-slate-300">
                              <span className="text-[10px] text-sky-400 block mb-1">
                                Rollback Safety Plan:
                              </span>
                              {investigation.recovery_plan.rollback_plan}
                            </div>
                          </div>
                        </div>

                        {/* Human Approval Gate Box */}
                        <div className="p-4 rounded-xl bg-[#0b132b] border border-[#1e2e54] space-y-4">
                          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                            <div className="flex items-center gap-3">
                              <UserCheck className="w-5 h-5 text-sky-400 flex-shrink-0" />
                              <div>
                                <p className="text-xs font-semibold text-white">
                                  Authorization:{" "}
                                  <span
                                    className={`font-mono ${
                                      investigation.recovery_plan.is_approved === true
                                        ? "text-emerald-400 font-bold"
                                        : investigation.recovery_plan.is_approved === false
                                        ? "text-rose-400 font-bold"
                                        : "text-amber-400 font-bold"
                                    }`}
                                  >
                                    {investigation.recovery_plan.is_approved === true
                                      ? "APPROVED"
                                      : investigation.recovery_plan.is_approved === false
                                      ? "REJECTED"
                                      : "AWAITING OPERATOR APPROVAL"}
                                  </span>
                                </p>
                                <p className="text-[11px] text-slate-400 font-mono">
                                  {investigation.recovery_plan.is_approved
                                    ? `Authorized by ${investigation.recovery_plan.approved_by || "SRE Operator"}`
                                    : "Review expected signal and risk level before execution."}
                                </p>
                              </div>
                            </div>

                            {investigation.current_stage === "AWAITING_APPROVAL" && (
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => handleApprove("approve")}
                                  className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-md transition cursor-pointer"
                                >
                                  Approve Action
                                </button>
                                <button
                                  onClick={() => handleApprove("reject")}
                                  className="px-3.5 py-2 rounded-lg bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800 text-xs font-semibold transition cursor-pointer"
                                >
                                  Reject
                                </button>
                              </div>
                            )}

                            {investigation.recovery_plan.is_approved &&
                              !investigation.recovery_plan.executed && (
                                <div className="flex items-center gap-2">
                                  <button
                                    onClick={() => handleTriggerRecoveryPrompt(false)}
                                    className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-slate-950 font-bold text-xs shadow-md transition cursor-pointer"
                                  >
                                    Execute Recovery
                                  </button>
                                  <button
                                    onClick={() => handleTriggerRecoveryPrompt(true)}
                                    className="px-3.5 py-2 rounded-lg bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-800 text-xs font-semibold transition cursor-pointer"
                                    title="Demonstrates dynamic replanning on verification check failure"
                                  >
                                    Inject Failure & Replan
                                  </button>
                                </div>
                              )}
                          </div>

                          {investigation.current_stage === "AWAITING_APPROVAL" && (
                            <div className="pt-2 border-t border-[#1e2e54]">
                              <label className="text-[11px] text-slate-400 font-mono block mb-1">
                                Operator Authorization Notes:
                              </label>
                              <input
                                type="text"
                                value={operatorNotes}
                                onChange={(e) => setOperatorNotes(e.target.value)}
                                className="w-full bg-[#131d38] border border-[#1e2e54] rounded-lg px-3 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-sky-500"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="py-8 text-center text-xs text-slate-400 font-mono">
                        Remediation action awaiting diagnostic root cause confirmation.
                      </div>
                    )}
                  </div>

                  {/* Post-Recovery SLA Verification Table */}
                  {investigation.verification_result && (
                    <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-6 shadow-xl">
                      <div className="flex items-center justify-between pb-4 border-b border-[#1e2e54]">
                        <h3 className="text-sm font-bold text-white flex items-center gap-2">
                          <ShieldCheck className="w-4 h-4 text-emerald-400" />
                          Post-Recovery SLA Verification
                        </h3>
                        <span
                          className={`text-xs font-mono uppercase px-2.5 py-1 rounded border font-bold ${
                            investigation.verification_result.verified
                              ? "bg-emerald-950 text-emerald-300 border-emerald-600"
                              : "bg-rose-950 text-rose-300 border-rose-600"
                          }`}
                        >
                          {investigation.verification_result.verified
                            ? "ALL CHECKS PASSED"
                            : "VERIFICATION FAILED (REPLAN REQUIRED)"}
                        </span>
                      </div>

                      <div className="mt-4 overflow-x-auto">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-[#0b132b] text-[11px] font-mono text-sky-400 uppercase border-b border-[#1e2e54]">
                            <tr>
                              <th className="px-4 py-2.5">SLA Metric</th>
                              <th className="px-4 py-2.5">Target Threshold</th>
                              <th className="px-4 py-2.5">Post-Recovery Value</th>
                              <th className="px-4 py-2.5">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#1e2e54]">
                            {investigation.verification_result.checks.map((c, i) => (
                              <tr key={i} className="hover:bg-[#182344]/50 font-mono">
                                <td className="px-4 py-3 text-slate-200 font-semibold">{c.metric}</td>
                                <td className="px-4 py-3 text-slate-400">{c.threshold}</td>
                                <td className="px-4 py-3 text-sky-300 font-bold">{c.value}</td>
                                <td className="px-4 py-3">
                                  <span
                                    className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                                      c.passed
                                        ? "bg-emerald-950 text-emerald-400 border-emerald-700"
                                        : "bg-rose-950 text-rose-400 border-rose-700"
                                    }`}
                                  >
                                    {c.passed ? "PASSED" : "FAILED"}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      <div className="mt-3 text-xs text-slate-300 font-mono bg-[#0b132b] p-2.5 rounded-lg border border-[#1e2e54]">
                        <strong>Outcome:</strong> {investigation.verification_result.outcome_summary}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-8 text-center text-xs text-slate-400 font-mono">
                  Loading recovery data...
                </div>
              )}
            </div>
          )}

          {/* TAB 7: TRACKER */}
          {activeTab === "tracker" && tracker && (
            <div className="space-y-6 animate-fadeIn">
              <InvestigationTracker
                tracker={tracker}
                onInspectEvidenceId={(id) => {
                  const ev = timeline?.events.find((e) => String(e.evidence_id) === id);
                  if (ev) setInspectingEvidence(ev);
                }}
              />
            </div>
          )}
        </main>
      </div>

      {/* Confirmation Modal before Executing Recovery */}
      {showRecoveryConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-amber-950 border border-amber-700/60 flex items-center justify-center text-amber-400 flex-shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white">Confirm Simulated Recovery</h3>
                <p className="text-xs text-slate-400 font-mono">
                  Target Service: {investigation?.recovery_plan?.affected_services?.join(", ") || "Active Infrastructure"}
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to execute{" "}
              <strong className="text-sky-300">{investigation?.recovery_plan?.action_name}</strong>?
              {pendingForceFailure && (
                <span className="block mt-2 text-amber-300 font-mono bg-amber-950/60 p-2 rounded border border-amber-800/80">
                  ⚠️ Synthetic Failure Mode enabled: telemetry will fail SLA checks to demonstrate the autonomous replanning loop.
                </span>
              )}
            </p>

            <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-[#1e2e54]">
              <button
                onClick={() => setShowRecoveryConfirm(false)}
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:bg-[#182344] transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmRecoveryExecution}
                className="px-4 py-1.5 rounded-lg text-xs font-bold bg-sky-600 hover:bg-sky-500 text-slate-950 shadow-md transition cursor-pointer"
              >
                Confirm & Execute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modals */}
      <EvidenceDetailModal
        evidence={inspectingEvidence}
        onClose={() => setInspectingEvidence(null)}
      />

      <EvidenceBundleModal
        bundle={showBundleModal ? bundle : null}
        onClose={() => setShowBundleModal(false)}
      />
    </div>
  );
}

export default function IncidentsWorkspacePage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[#0b132b] text-slate-300">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-sky-500/20 border-t-sky-500 rounded-full animate-spin" />
            <p className="text-xs text-sky-400 font-mono">
              Loading VeriOps Operations Center...
            </p>
          </div>
        </div>
      }
    >
      <IncidentsWorkspaceContent />
    </React.Suspense>
  );
}
