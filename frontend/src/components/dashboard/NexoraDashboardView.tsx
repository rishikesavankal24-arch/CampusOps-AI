"use client";

import React, { useState } from "react";
import {
  IncidentSummary,
  IncidentTimelineResponse,
  ServiceDependencyGraphResponse,
} from "@/types/incident";
import {
  InvestigationStateResponse,
  InvestigationTrackerResponse,
  HardwareDeviceImpact,
} from "@/types/investigation";
import {
  Flame,
  CheckCircle2,
  Clock,
  Layers,
  ShieldCheck,
  TrendingUp,
  Network,
  ArrowRight,
  Play,
  BarChart3,
  Bot,
  UserCheck,
} from "lucide-react";

interface NexoraDashboardViewProps {
  incident: IncidentSummary | null;
  allIncidents?: IncidentSummary[];
  timeline: IncidentTimelineResponse | null;
  graph: ServiceDependencyGraphResponse | null;
  investigation: InvestigationStateResponse | null;
  tracker: InvestigationTrackerResponse | null;
  onNavigateToTab: (tab: string) => void;
  onSelectIncident?: (incidentId: string) => void;
  onTriggerDemo: () => Promise<void>;
  onRunNextDiagnostic: () => Promise<void>;
}

export default function NexoraDashboardView({
  incident,
  allIncidents = [],
  timeline,
  graph,
  investigation,
  tracker,
  onNavigateToTab,
  onSelectIncident,
  onTriggerDemo,
  onRunNextDiagnostic,
}: NexoraDashboardViewProps) {
  const [runningAction, setRunningAction] = useState(false);

  const leadingHypothesis = investigation?.hypotheses.find(
    (h) => h.id === investigation.leading_hypothesis_id
  );
  const leadingConf = leadingHypothesis?.confidence_score || 0.78;
  const isResolved = investigation?.current_stage === "RESOLVED";
  const isAwaitingApproval = investigation?.current_stage === "AWAITING_APPROVAL";
  const isReplanning = investigation?.current_stage === "REPLANNING";

  // Dynamic KPI calculations
  const activeIncidentsCount = allIncidents.length > 0
    ? allIncidents.filter((i) => i.status !== "resolved").length
    : isResolved ? 0 : 1;

  const totalServices = graph?.nodes.length || 6;
  const degradedServices = isResolved
    ? 0
    : graph?.nodes.filter((n) => n.status !== "healthy").length || 2;

  const affectedUsersCount = isResolved ? 0 : 420;

  const mttiDisplay = tracker?.elapsed_seconds
    ? `${(tracker.elapsed_seconds / 60).toFixed(1)}m`
    : "1.8m";

  // Telemetry points reflecting actual verification state
  const finalLatency = isResolved
    ? 240
    : isReplanning
    ? 9420
    : 10820;

  const finalErrorRate = isResolved
    ? 0.02
    : isReplanning
    ? 11.5
    : 14.8;

  const telemetryPoints = [
    { time: "09:00", latency: 240, errorRate: 0.1 },
    { time: "09:05", latency: 380, errorRate: 0.4 },
    { time: "09:10", latency: 920, errorRate: 2.1 },
    { time: "09:12", latency: 4200, errorRate: 6.8 },
    { time: "09:14", latency: 10820, errorRate: 14.8 },
    { time: "09:18", latency: 10540, errorRate: 14.2 },
    { time: "09:20", latency: 11420, errorRate: 15.2 },
    { time: "09:25", latency: finalLatency, errorRate: finalErrorRate },
  ];

  const handleAction = async (fn: () => Promise<void>) => {
    try {
      setRunningAction(true);
      await fn();
    } finally {
      setRunningAction(false);
    }
  };

  return (
    <div className="space-y-6 font-sans">
      {/* =========================================================================
          5 KPI CARDS: Calm, enterprise-grade dark palette
          ========================================================================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* KPI 1: Active Incidents */}
        <div
          onClick={() => onNavigateToTab("incidents")}
          className="bg-[#131d38] border border-[#1e2e54] hover:border-blue-500/50 p-4 rounded-xl transition cursor-pointer shadow-sm group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono text-[11px] uppercase tracking-wider">Active Incidents</span>
            <Flame className="w-4 h-4 text-rose-400 group-hover:scale-105 transition-transform" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {activeIncidentsCount}
            </span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold uppercase ${
                activeIncidentsCount === 0
                  ? "bg-emerald-950/70 text-emerald-400 border border-emerald-800/60"
                  : "bg-rose-950/70 text-rose-300 border border-rose-800/60"
              }`}
            >
              {activeIncidentsCount === 0 ? "Normal" : "Action Needed"}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1 block group-hover:text-blue-400 transition-colors">
            {activeIncidentsCount === 0 ? "All incidents resolved" : "1 critical incident open"}
          </span>
        </div>

        {/* KPI 2: Service Health */}
        <div
          onClick={() => onNavigateToTab("topology")}
          className="bg-[#131d38] border border-[#1e2e54] hover:border-blue-500/50 p-4 rounded-xl transition cursor-pointer shadow-sm group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono text-[11px] uppercase tracking-wider">Service Health</span>
            <Layers className="w-4 h-4 text-blue-400 group-hover:scale-105 transition-transform" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {totalServices - degradedServices} / {totalServices}
            </span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold uppercase ${
                degradedServices === 0
                  ? "bg-emerald-950/70 text-emerald-400 border border-emerald-800/60"
                  : "bg-amber-950/70 text-amber-300 border border-amber-800/60"
              }`}
            >
              {degradedServices === 0 ? "Operational" : `${degradedServices} Degraded`}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1 block">
            {degradedServices === 0 ? "All services healthy" : "gateway & identity affected"}
          </span>
        </div>

        {/* KPI 3: Affected Users */}
        <div
          onClick={() => onNavigateToTab("evidence")}
          className="bg-[#131d38] border border-[#1e2e54] hover:border-blue-500/50 p-4 rounded-xl transition cursor-pointer shadow-sm group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono text-[11px] uppercase tracking-wider">Affected Users</span>
            <TrendingUp className="w-4 h-4 text-rose-400 group-hover:scale-105 transition-transform" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {affectedUsersCount}
            </span>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold uppercase ${
                isResolved
                  ? "bg-emerald-950/70 text-emerald-400 border border-emerald-800/60"
                  : "bg-rose-950/70 text-rose-300 border border-rose-800/60"
              }`}
            >
              {isResolved ? "0.8% Fail" : "84.2% Peak"}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1 block">
            {timeline?.filtered_events || 11} correlated evidence items
          </span>
        </div>

        {/* KPI 4: Mean Time to Investigate (MTTI) */}
        <div
          onClick={() => onNavigateToTab("tracker")}
          className="bg-[#131d38] border border-[#1e2e54] hover:border-blue-500/50 p-4 rounded-xl transition cursor-pointer shadow-sm group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono text-[11px] uppercase tracking-wider">Investigation Time</span>
            <Clock className="w-4 h-4 text-sky-400 group-hover:scale-105 transition-transform" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-100 font-mono">{mttiDisplay}</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sky-950/70 text-sky-300 border border-sky-800/60 font-semibold uppercase">
              Autonomous
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1 block">
            13-stage verification cycle
          </span>
        </div>

        {/* KPI 5: Recovery Status */}
        <div
          onClick={() => onNavigateToTab("recovery")}
          className="bg-[#131d38] border border-[#1e2e54] hover:border-blue-500/50 p-4 rounded-xl transition cursor-pointer shadow-sm group"
        >
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-mono text-[11px] uppercase tracking-wider">Recovery Status</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400 group-hover:scale-105 transition-transform" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-base font-bold text-slate-100 font-mono truncate">
              {isResolved
                ? "Verified Pass"
                : isAwaitingApproval
                ? "Approval Gate"
                : isReplanning
                ? "Replanning"
                : investigation?.current_stage || "Investigating"}
            </span>
          </div>
          <span className="text-[10px] text-slate-400 font-mono mt-1 block">
            {isResolved
              ? "4/4 SLA checks passed"
              : isAwaitingApproval
              ? "Operator approval required"
              : "Diagnostics in progress"}
          </span>
        </div>
      </div>

      {/* =========================================================================
          MAIN 2-COLUMN LAYOUT: Main column (chart & incident) + Side column (AI & devices)
          ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* =================== MAIN COLUMN (2 cols) =================== */}
        <div className="lg:col-span-2 space-y-6">
          {/* 1. Ingress Telemetry Chart */}
          <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#1e2e54] pb-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                  Gateway Telemetry & Anomaly Activity
                </h3>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 bg-rose-500 rounded" />
                  <span className="text-slate-300">P99 Latency (ms)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-1 bg-amber-400 rounded" />
                  <span className="text-slate-300">HTTP 504 %</span>
                </div>
              </div>
            </div>

            {/* SVG Telemetry Chart */}
            <div className="w-full h-44 relative bg-[#0b1329] rounded-lg p-2 border border-[#1e2e54]/60 overflow-hidden">
              <svg
                viewBox="0 0 700 170"
                className="w-full h-full"
                preserveAspectRatio="none"
              >
                <defs>
                  <linearGradient id="latencyAreaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ef4444" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#ef4444" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Gridlines */}
                <line x1="60" y1="25" x2="660" y2="25" stroke="#1e2e54" strokeDasharray="3 3" />
                <line x1="60" y1="65" x2="660" y2="65" stroke="#1e2e54" strokeDasharray="3 3" />
                <line x1="60" y1="105" x2="660" y2="105" stroke="#1e2e54" strokeDasharray="3 3" />
                <line x1="60" y1="145" x2="660" y2="145" stroke="#1e2e54" />

                {/* Y-Axis Labels */}
                <text x="50" y="29" fill="#64748b" fontSize="9" fontFamily="monospace" textAnchor="end">12s</text>
                <text x="50" y="69" fill="#64748b" fontSize="9" fontFamily="monospace" textAnchor="end">8s</text>
                <text x="50" y="109" fill="#64748b" fontSize="9" fontFamily="monospace" textAnchor="end">4s</text>
                <text x="50" y="148" fill="#64748b" fontSize="9" fontFamily="monospace" textAnchor="end">0s</text>

                {/* Latency Area */}
                <path
                  d={
                    isResolved
                      ? "M 60 142 L 140 138 L 220 132 L 300 95 L 380 25 L 460 28 L 540 22 L 640 142 L 640 145 L 60 145 Z"
                      : "M 60 142 L 140 138 L 220 132 L 300 95 L 380 25 L 460 28 L 540 22 L 640 30 L 640 145 L 60 145 Z"
                  }
                  fill="url(#latencyAreaGradient)"
                />

                {/* Latency Line */}
                <path
                  d={
                    isResolved
                      ? "M 60 142 L 140 138 L 220 132 L 300 95 L 380 25 L 460 28 L 540 22 L 640 142"
                      : "M 60 142 L 140 138 L 220 132 L 300 95 L 380 25 L 460 28 L 540 22 L 640 30"
                  }
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="2"
                />

                {/* Error Rate Line */}
                <path
                  d={
                    isResolved
                      ? "M 60 144 L 140 143 L 220 141 L 300 120 L 380 50 L 460 52 L 540 48 L 640 144"
                      : "M 60 144 L 140 143 L 220 141 L 300 120 L 380 50 L 460 52 L 540 48 L 640 54"
                  }
                  fill="none"
                  stroke="#f59e0b"
                  strokeWidth="2"
                  strokeDasharray="4 2"
                />

                {/* Peak Anomaly Circle */}
                <circle cx="380" cy="25" r="4" fill="#ef4444" />
                <circle cx="640" cy={isResolved ? 142 : 30} r="4" fill={isResolved ? "#10b981" : "#ef4444"} />

                {/* X-Axis Time Labels */}
                {telemetryPoints.map((pt, i) => {
                  const x = 60 + i * 82;
                  return (
                    <text
                      key={pt.time}
                      x={x}
                      y="162"
                      fill="#64748b"
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {pt.time}
                    </text>
                  );
                })}
              </svg>

              {/* Status Overlay Badge */}
              <div className="absolute top-3 right-3 flex items-center gap-2">
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold ${
                    isResolved
                      ? "bg-emerald-950/80 text-emerald-400 border-emerald-800"
                      : "bg-rose-950/80 text-rose-300 border-rose-800"
                  }`}
                >
                  {isResolved ? "Telemetry Normal (240ms P99)" : "Active Anomaly: 10.82s (+801%)"}
                </span>
              </div>
            </div>
          </div>

          {/* 2. Current Incident Summary Card */}
          {incident && (
            <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1e2e54] pb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border font-bold ${
                        incident.status === "resolved"
                          ? "bg-emerald-950/70 text-emerald-400 border-emerald-800"
                          : "bg-rose-950/70 text-rose-300 border-rose-800"
                      }`}
                    >
                      {incident.priority.toUpperCase()}
                    </span>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#0b1329] text-slate-300 border border-[#1e2e54]">
                      Status: {incident.status}
                    </span>
                    <span className="text-[10px] font-mono text-slate-400">
                      ID: {incident.id.slice(0, 13)}...
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-slate-100">{incident.title}</h2>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onNavigateToTab("investigation")}
                    className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition cursor-pointer flex items-center gap-1.5 shadow"
                  >
                    <span>Open Investigation</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Incident Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div className="bg-[#0b1329] p-2.5 rounded-lg border border-[#1e2e54]">
                  <span className="text-slate-400 text-[10px] block">Ingress P99 Latency</span>
                  <span className={`font-bold ${isResolved ? "text-emerald-400" : "text-rose-400"}`}>
                    {isResolved ? "240ms" : "10.82s"}
                  </span>
                </div>
                <div className="bg-[#0b1329] p-2.5 rounded-lg border border-[#1e2e54]">
                  <span className="text-slate-400 text-[10px] block">HTTP 504 Rate</span>
                  <span className={`font-bold ${isResolved ? "text-emerald-400" : "text-rose-400"}`}>
                    {isResolved ? "0.02%" : "14.8%"}
                  </span>
                </div>
                <div className="bg-[#0b1329] p-2.5 rounded-lg border border-[#1e2e54]">
                  <span className="text-slate-400 text-[10px] block">DB Pool Utilization</span>
                  <span className={`font-bold ${isResolved ? "text-emerald-400" : "text-amber-400"}`}>
                    {isResolved ? "14/50 (28%)" : "15/15 (100%)"}
                  </span>
                </div>
                <div className="bg-[#0b1329] p-2.5 rounded-lg border border-[#1e2e54]">
                  <span className="text-slate-400 text-[10px] block">Evidence Correlated</span>
                  <span className="text-sky-300 font-bold">
                    {timeline?.filtered_events || 11} items
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* 3. Recent Incidents Table */}
          {allIncidents.length > 0 && (
            <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-[#1e2e54] pb-3">
                <div className="flex items-center gap-2">
                  <Flame className="w-4 h-4 text-rose-400" />
                  <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                    Recent Incident Queue ({allIncidents.length})
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-slate-400">
                  Click to switch incident
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[#0b1329] text-[10px] font-mono text-slate-400 uppercase border-b border-[#1e2e54]">
                    <tr>
                      <th className="px-3 py-2">Priority</th>
                      <th className="px-3 py-2">Incident Title</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Evidence</th>
                      <th className="px-3 py-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e2e54]/50 font-mono text-xs">
                    {allIncidents.map((inc) => {
                      const isCurrent = incident?.id === inc.id;
                      return (
                        <tr
                          key={inc.id}
                          className={`hover:bg-[#182344] transition-colors ${
                            isCurrent ? "bg-[#182344]/80" : ""
                          }`}
                        >
                          <td className="px-3 py-2.5">
                            <span
                              className={`text-[9px] font-bold px-1.5 py-0.2 rounded border ${
                                inc.priority === "critical"
                                  ? "bg-rose-950/70 text-rose-400 border-rose-800"
                                  : "bg-amber-950/70 text-amber-400 border-amber-800"
                              }`}
                            >
                              {inc.priority.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 font-sans font-semibold text-slate-200">
                            {inc.title}
                          </td>
                          <td className="px-3 py-2.5">
                            <span
                              className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                                inc.status === "resolved"
                                  ? "text-emerald-400"
                                  : "text-amber-400"
                              }`}
                            >
                              {inc.status}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 text-slate-400">
                            {inc.evidence_count} items
                          </td>
                          <td className="px-3 py-2.5 text-right">
                            {isCurrent ? (
                              <span className="text-[10px] text-sky-400 font-semibold">Active</span>
                            ) : (
                              <button
                                onClick={() => onSelectIncident && onSelectIncident(inc.id)}
                                className="text-[10px] text-blue-400 hover:text-blue-200 underline cursor-pointer"
                              >
                                Select
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* =================== SIDE COLUMN (1 col) =================== */}
        <div className="space-y-6">
          {/* AI Investigation Insight Panel */}
          <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#1e2e54] pb-3">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                  AI Investigation Insight
                </h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0b1329] text-sky-400 border border-[#1e2e54]">
                STAGE: {investigation?.current_stage || "DIAGNOSING"}
              </span>
            </div>

            {/* Leading Root Cause Hypothesis */}
            {leadingHypothesis && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-slate-400 text-[11px]">Leading Hypothesis:</span>
                  <span className="font-mono font-bold text-sky-300">
                    {leadingHypothesis.id} ({Math.round(leadingConf * 100)}% Conf.)
                  </span>
                </div>

                {/* Confidence Bar */}
                <div className="w-full h-2 bg-[#0b1329] rounded-full overflow-hidden border border-[#1e2e54]">
                  <div
                    className={`h-full transition-all duration-500 ${
                      leadingConf >= 0.8
                        ? "bg-emerald-400"
                        : leadingConf >= 0.5
                        ? "bg-sky-400"
                        : "bg-amber-400"
                    }`}
                    style={{ width: `${Math.round(leadingConf * 100)}%` }}
                  />
                </div>

                <h4 className="text-xs font-bold text-slate-100 leading-snug">
                  {leadingHypothesis.title}
                </h4>

                <div className="text-[11px] text-slate-300 font-mono bg-[#0b1329] p-2.5 rounded-lg border border-[#1e2e54] flex items-center justify-between">
                  <span className="truncate">Root Cause: DB connection pool starvation (15/15)</span>
                  <button
                    onClick={() => onNavigateToTab("investigation")}
                    className="text-sky-400 hover:text-sky-200 underline shrink-0 ml-2 text-[10px]"
                  >
                    Inspect &rarr;
                  </button>
                </div>
              </div>
            )}

            {/* Evidence Rationale Breakdown */}
            <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-1">
              <div className="bg-[#0b1329] p-2 rounded border border-[#1e2e54]">
                <span className="text-emerald-400 font-bold block">
                  &bull; {leadingHypothesis?.supporting_evidence_ids.length || 6} Supporting
                </span>
                <span className="text-slate-400">Traces, logs, metrics</span>
              </div>
              <div className="bg-[#0b1329] p-2 rounded border border-[#1e2e54]">
                <span className="text-rose-400 font-bold block">
                  &bull; {leadingHypothesis?.contradicting_evidence_ids.length || 0} Contradicting
                </span>
                <span className="text-slate-400">Network L3/L4 clear</span>
              </div>
            </div>

            {/* Affected Services Pills */}
            <div className="space-y-1.5 text-xs">
              <span className="text-[11px] font-mono text-slate-400 block">
                Affected Services:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {["portal-gateway", "auth-service", "campusops-db"].map((svc) => (
                  <span
                    key={svc}
                    className="bg-[#0b1329] text-sky-300 border border-[#1e2e54] px-2 py-0.5 rounded text-[10px] font-mono"
                  >
                    {svc}
                  </span>
                ))}
              </div>
            </div>

            {/* Recommended Next Action Button */}
            <div className="pt-3 border-t border-[#1e2e54] space-y-2">
              <span className="text-[11px] text-slate-400 font-mono block">
                Recommended Action:
              </span>
              {isResolved ? (
                <div className="space-y-2">
                  <div className="p-2.5 rounded-lg bg-emerald-950/70 border border-emerald-700/60 text-emerald-300 text-xs font-mono font-bold flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" /> Incident Resolved
                  </div>
                  <button
                    onClick={() => handleAction(onTriggerDemo)}
                    disabled={runningAction}
                    className="w-full py-2 px-3 rounded-lg bg-[#0b1329] hover:bg-[#172344] border border-[#1e2e54] text-slate-200 text-xs font-bold transition flex items-center justify-center gap-1.5 shadow cursor-pointer disabled:opacity-50"
                  >
                    <Play className="w-3.5 h-3.5 text-sky-400" /> Trigger New Demo Incident
                  </button>
                </div>
              ) : isAwaitingApproval ? (
                <button
                  onClick={() => onNavigateToTab("recovery")}
                  className="w-full py-2 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-slate-950 text-xs font-bold transition flex items-center justify-center gap-1.5 shadow cursor-pointer"
                >
                  <UserCheck className="w-4 h-4" /> Review & Approve Recovery Plan
                </button>
              ) : (
                <button
                  onClick={() => handleAction(onRunNextDiagnostic)}
                  disabled={runningAction}
                  className="w-full py-2 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center justify-center gap-1.5 shadow cursor-pointer disabled:opacity-50"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {runningAction ? "Running..." : "Run Next Diagnostic Tool"}
                </button>
              )}
            </div>
          </div>

          {/* Service & Hardware Digital Twin Health */}
          <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 space-y-3 shadow-sm">
            <div className="flex items-center justify-between border-b border-[#1e2e54] pb-3">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-sky-400" />
                <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
                  Network Devices
                </h3>
              </div>
              <button
                onClick={() => onNavigateToTab("topology")}
                className="text-xs text-sky-400 hover:text-sky-200 underline font-mono cursor-pointer"
              >
                Topology &rarr;
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {(
                tracker?.device_mapping || [
                  {
                    device_name: "switch-core-bldg-a",
                    device_type: "switch",
                    ip_address: "10.0.1.1",
                    location: "Rack 2",
                    status: "HEALTHY",
                    health_summary: {},
                    impacted_services: ["portal-gateway", "auth-service"],
                    technician_recommendation: null,
                    simulated: true,
                  },
                  {
                    device_name: "gw-border-01",
                    device_type: "gateway",
                    ip_address: "10.0.0.1",
                    location: "Border DMZ",
                    status: "HEALTHY",
                    health_summary: {},
                    impacted_services: ["portal-gateway"],
                    technician_recommendation: null,
                    simulated: true,
                  },
                  {
                    device_name: "ap-lib-floor2",
                    device_type: "access_point",
                    ip_address: "10.0.4.15",
                    location: "Library 2F",
                    status: "HEALTHY",
                    health_summary: {},
                    impacted_services: ["student-portal-ui"],
                    technician_recommendation: null,
                    simulated: true,
                  },
                  {
                    device_name: "dns-campus-primary",
                    device_type: "dns_resolver",
                    ip_address: "10.0.0.53",
                    location: "NOC",
                    status: "HEALTHY",
                    health_summary: {},
                    impacted_services: ["portal-gateway"],
                    technician_recommendation: null,
                    simulated: true,
                  },
                ]
              ).map((dev: HardwareDeviceImpact) => (
                <div
                  key={dev.device_name}
                  className="bg-[#0b1329] border border-[#1e2e54] rounded-lg p-2.5 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-200 truncate">
                      {dev.device_name}
                    </span>
                    <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800/60 font-semibold">
                      {dev.status}
                    </span>
                  </div>
                  <div className="text-[10px] font-mono text-slate-400">
                    {dev.device_type} &bull; {dev.ip_address}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
