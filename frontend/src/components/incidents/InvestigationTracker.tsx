"use client";

import React, { useState } from "react";
import {
  InvestigationTrackerResponse,
  TrackerStageEvent,
  HardwareDeviceImpact,
} from "@/types/investigation";
import {
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Clock,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Network,
  Filter,
} from "lucide-react";

interface InvestigationTrackerProps {
  tracker: InvestigationTrackerResponse | null;
  onInspectEvidenceId?: (id: string) => void;
}

export default function InvestigationTracker({
  tracker,
  onInspectEvidenceId,
}: InvestigationTrackerProps) {
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [expandedStageId, setExpandedStageId] = useState<number | null>(null);
  const [showDeviceDetails, setShowDeviceDetails] = useState<boolean>(true);

  if (!tracker) return null;

  const filteredStages =
    selectedCategory === "all"
      ? tracker.stages
      : tracker.stages.filter((s) => s.category === selectedCategory);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case "IN_PROGRESS":
        return <Play className="w-3.5 h-3.5 text-sky-400 fill-current animate-pulse" />;
      case "BLOCKED":
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case "REPLANNING":
        return <RotateCcw className="w-4 h-4 text-rose-400" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-slate-600" />;
    }
  };

  const getStatusClasses = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return "border-emerald-700/60 bg-emerald-950/30 text-emerald-300";
      case "IN_PROGRESS":
        return "border-sky-500 bg-sky-950/40 text-sky-200 shadow-sm";
      case "BLOCKED":
        return "border-amber-500 bg-amber-950/40 text-amber-200";
      case "REPLANNING":
        return "border-rose-600 bg-rose-950/40 text-rose-200";
      default:
        return "border-[#1e2e54] bg-[#0b1329] text-slate-500";
    }
  };

  const completedCount = tracker.summary_counts.completed || 0;
  const progressPercent = Math.round((completedCount / tracker.stages.length) * 100);

  const formatElapsed = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = sec % 60;
    return `${mins}m ${s < 10 ? `0${s}` : s}s`;
  };

  return (
    <div className="bg-[#131d38] border border-[#1e2e54] rounded-xl p-5 space-y-6 shadow-sm">
      {/* Header & Overall Stepper Progress */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#1e2e54] pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-sky-400" />
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
              Investigation Tracker & Audit Trail
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#0b1329] text-sky-300 border border-[#1e2e54]">
              13 MILESTONES
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            Active Milestone {tracker.current_stage_id} / 13:{" "}
            <strong className="text-slate-100">{tracker.current_stage_name}</strong>
          </p>
        </div>

        {/* Overall Completion & Elapsed Time */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="bg-[#0b1329] border border-[#1e2e54] px-3 py-1.5 rounded-lg flex items-center gap-2 font-mono text-xs">
            <Clock className="w-3.5 h-3.5 text-sky-400" />
            <span className="text-slate-400">Elapsed:</span>
            <span className="text-slate-100 font-bold">
              {formatElapsed(tracker.elapsed_seconds)}
            </span>
          </div>

          <div className="bg-[#0b1329] border border-[#1e2e54] px-3 py-1.5 rounded-lg flex items-center gap-2 font-mono text-xs">
            <span className="text-slate-400">Progress:</span>
            <span className="text-emerald-400 font-bold">{progressPercent}%</span>
            <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-slate-400 flex items-center gap-1 mr-1 font-mono text-[11px]">
            <Filter className="w-3 h-3 text-sky-400" /> Filter:
          </span>
          {[
            { id: "all", label: `All (${tracker.stages.length})` },
            { id: "investigation", label: "Investigation (4)" },
            { id: "diagnostics", label: "Diagnostics (2)" },
            { id: "recovery", label: "Recovery (3)" },
            { id: "verification", label: "Verification (2)" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedCategory(tab.id)}
              className={`px-2.5 py-1 rounded font-mono text-[11px] transition cursor-pointer ${
                selectedCategory === tab.id
                  ? "bg-blue-600 text-white font-bold shadow-sm"
                  : "bg-[#0b1329] text-slate-400 border border-[#1e2e54] hover:bg-[#182344] hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Status Count Badges */}
        <div className="flex items-center gap-2 font-mono text-[10px]">
          <span className="px-2 py-0.5 rounded bg-emerald-950/70 text-emerald-300 border border-emerald-800/60 font-semibold">
            {tracker.summary_counts.completed || 0} Done
          </span>
          {(tracker.summary_counts.in_progress || 0) > 0 && (
            <span className="px-2 py-0.5 rounded bg-sky-950/70 text-sky-300 border border-sky-800/60 font-semibold animate-pulse">
              {tracker.summary_counts.in_progress} Active
            </span>
          )}
          {(tracker.summary_counts.blocked || 0) > 0 && (
            <span className="px-2 py-0.5 rounded bg-amber-950/70 text-amber-300 border border-amber-800/60 font-semibold">
              {tracker.summary_counts.blocked} Blocked
            </span>
          )}
        </div>
      </div>

      {/* 13-Stage Chronological Execution List */}
      <div className="space-y-2.5">
        {filteredStages.map((stage: TrackerStageEvent) => {
          const isExpanded = expandedStageId === stage.stage_id;

          return (
            <div
              key={stage.stage_id}
              className={`border rounded-xl p-3.5 text-xs transition-all ${getStatusClasses(
                stage.status
              )}`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-[#0b1329] border border-[#1e2e54]/80 flex items-center justify-center shrink-0">
                    {getStatusIcon(stage.status)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] font-bold text-slate-100">
                        Stage {stage.stage_id}: {stage.stage_name}
                      </span>
                      <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-[#0b1329] text-slate-300 border border-[#1e2e54]">
                        {stage.category}
                      </span>
                      {stage.tool_name && (
                        <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#182344] text-sky-300 border border-sky-800">
                          {stage.tool_name}
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-300 mt-0.5 font-sans">
                      {stage.summary}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0 font-mono text-[10px]">
                  {stage.timestamp && (
                    <span className="text-slate-400">
                      {new Date(stage.timestamp).toLocaleTimeString()}
                    </span>
                  )}
                  <button
                    onClick={() =>
                      setExpandedStageId(isExpanded ? null : stage.stage_id)
                    }
                    className="p-1 rounded bg-[#0b1329] border border-[#1e2e54] hover:bg-[#182344] text-slate-300 hover:text-white transition cursor-pointer flex items-center gap-1"
                  >
                    <span>{isExpanded ? "Hide" : "Details"}</span>
                    {isExpanded ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
                    )}
                  </button>
                </div>
              </div>

              {/* Expandable Details & Correlated Evidence Links */}
              {isExpanded && (
                <div className="mt-3 pt-3 border-t border-[#1e2e54]/80 space-y-2 font-mono text-[11px] animate-fadeIn">
                  <div className="bg-[#070d1e] p-3 rounded-lg border border-[#1e2e54] text-slate-300 overflow-x-auto text-[10px]">
                    <span className="text-sky-400 block mb-1 font-bold">Execution Output / Parameters:</span>
                    <pre>{JSON.stringify(stage.details, null, 2)}</pre>
                  </div>

                  {stage.evidence_ids && stage.evidence_ids.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <span className="text-slate-400 text-[10px]">Linked Evidence:</span>
                      {stage.evidence_ids.map((id) => (
                        <button
                          key={id}
                          onClick={() => onInspectEvidenceId && onInspectEvidenceId(id)}
                          className="px-2 py-0.5 rounded bg-[#182344] text-sky-300 border border-sky-800 hover:border-sky-500 text-[10px] cursor-pointer"
                        >
                          {id.slice(0, 8)}...
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Network Hardware Digital Twin Mapping */}
      <div className="bg-[#0b1329] border border-[#1e2e54] rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-[#1e2e54] pb-2">
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-sky-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Campus Hardware Device Mapping ({tracker.device_mapping.length})
            </h3>
          </div>
          <button
            onClick={() => setShowDeviceDetails(!showDeviceDetails)}
            className="text-[11px] font-mono text-sky-400 hover:text-sky-200 underline cursor-pointer"
          >
            {showDeviceDetails ? "Collapse" : "Expand"}
          </button>
        </div>

        {showDeviceDetails && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
            {tracker.device_mapping.map((dev: HardwareDeviceImpact) => (
              <div
                key={dev.device_name}
                className="bg-[#131d38] border border-[#1e2e54] rounded-lg p-3 space-y-1.5"
              >
                <div className="flex items-center justify-between font-mono">
                  <span className="font-bold text-slate-100">{dev.device_name}</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800 font-semibold">
                    {dev.status}
                  </span>
                </div>
                <div className="text-[10px] font-mono text-slate-400">
                  IP: {dev.ip_address} &bull; Type: {dev.device_type}
                </div>
                <div className="text-[10px] font-mono text-slate-400 truncate">
                  Loc: {dev.location}
                </div>
                <div className="pt-1.5 border-t border-[#1e2e54] text-[10px] font-mono">
                  <span className="text-sky-400 block mb-0.5">Downstream Services:</span>
                  <div className="flex flex-wrap gap-1">
                    {dev.impacted_services.map((svc) => (
                      <span
                        key={svc}
                        className="px-1.5 py-0.2 rounded bg-[#0b1329] text-sky-300 border border-[#1e2e54]"
                      >
                        {svc}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
